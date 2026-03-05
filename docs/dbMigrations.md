# DB Migrations Workflow

This project uses SQLAlchemy + Alembic for PostgreSQL schema management.

## Baseline
- Baseline revision: `20260305_01` in `codexchat_back/alembic/versions/20260305_01_baseline.py`
- Baseline is intentionally empty and establishes migration history before schema tables are added.

## Environment
- Required env var: `DATABASE_URL`
- Expected format: PostgreSQL SQLAlchemy URL (example: `postgresql+psycopg://codexchat:codexchat@codexchat_db:5432/codexchat`)
- Validation is enforced at backend startup and Alembic runtime.

## Common Commands
From `codexchat_back/`:

```bash
# create a new migration file
alembic revision -m "short_description"

# create migration from SQLAlchemy model changes
alembic revision --autogenerate -m "describe_change"

# apply migrations
alembic upgrade head

# rollback one step
alembic downgrade -1

# show current DB revision
alembic current

# show migration history
alembic history
```

## Versioning Conventions
- One logical concern per migration when possible.
- Message format: `<domain>: <action>` (example: `core: create users table`).
- Keep downgrade path available when safe.
- Do not edit applied migration files; add a follow-up revision instead.

## Review Checklist
- Migration applies cleanly on empty DB.
- Migration applies cleanly over prior revisions.
- Downgrade path is present and tested where safe.
- Added/changed indexes and constraints match TODO scope.

## Conversation locks + stale recovery
- Added table: `conversation_locks` (revision `20260305_06`).
- Columns:
  - `conversation_id` (unique FK to `conversations.id`, `ON DELETE RESTRICT`)
  - `locked_by` (nullable FK to `users.id`, `ON DELETE SET NULL`)
  - `owner_token` (compare-and-release ownership token)
  - `locked_at`, `last_heartbeat_at`, `expires_at`
  - `stale_after_seconds` (per-lock stale TTL)
  - `metadata_json` (system/worker ownership details when `locked_by` is null)
  - `resource_type`, `resource_id` (normalized lock resource keys)
- Default TTL assumptions:
  - `stale_after_seconds` default is `120` seconds.
  - A lock is stale when `now() - last_heartbeat_at > stale_after_seconds`.
- Recovery procedure:
  - Acquire lock by writing `owner_token` and lock timestamps.
  - Lock owner updates `last_heartbeat_at` periodically while work is active.
  - Release/refresh operations must include `owner_token` match (compare-and-release).
  - If stale, a new owner can replace the row with a new `owner_token`.
- Required indexes:
  - `ix_conversation_locks_resource_type_resource_id` on (`resource_type`, `resource_id`)
  - `ix_conversation_locks_last_heartbeat_at` on `last_heartbeat_at`
  - `ix_conversation_locks_locked_by` on `locked_by`
- Backfill notes:
  - No backfill required for this initial lock table creation.

## Constraint policy (revision `20260305_08`)
- Foreign key policy:
  - Default: `ON DELETE RESTRICT` for core parent entities users care about.
  - Targeted `ON DELETE CASCADE` only for purely dependent/internal child rows.
- Applied relation rules:
  - `messages.conversation_id -> conversations.id` uses `ON DELETE CASCADE`.
  - `files.conversation_id -> conversations.id` uses `ON DELETE RESTRICT`.
  - `message_files.message_id -> messages.id` uses `ON DELETE CASCADE`.
  - `message_files.file_id -> files.id` uses `ON DELETE CASCADE`.
  - `sessions.user_id -> users.id` uses `ON DELETE RESTRICT`.
  - `settings.updated_by_user_id -> users.id` uses `ON DELETE SET NULL`.
  - `audit_logs.actor_user_id -> users.id` uses `ON DELETE RESTRICT`.
  - `audit_logs.target_user_id -> users.id` uses `ON DELETE SET NULL`.
  - `heartbeat_jobs.conversation_id -> conversations.id` uses `ON DELETE RESTRICT`.
  - `heartbeat_schedules.heartbeat_job_id -> heartbeat_jobs.id` uses `ON DELETE CASCADE`.
  - `conversation_locks.conversation_id -> conversations.id` uses `ON DELETE RESTRICT`.
- Value constraints:
  - `files.size_bytes >= 0`.
  - Role checks remain constrained to:
    - users: `user|admin`
    - messages: `user|assistant|system`

## Soft-delete archive semantics (`archived_at`)
- Archivable tables: `conversations`, `messages`, `files`, `heartbeat_jobs`.
- Standard semantics (all tables):
  - `archived_at IS NULL` => active row
  - `archived_at IS NOT NULL` => archived row
  - Column type is `TIMESTAMPTZ`; timestamps are DB-generated (`now()`), which Postgres stores in UTC internally.
- Query policy:
  - Default product queries must filter active rows only.
  - Admin/archive views must opt in explicitly (`include_archived=True` or `only_archived=True` in query layer).

### Migration-safe helper snippet (Alembic SQL)
Use explicit `WHERE archived_at IS NULL/IS NOT NULL` guards so the operation is idempotent and safe to rerun.

```python
# Alembic upgrade() example: archive one conversation and related rows.
op.execute(
    sa.text(
        """
        UPDATE conversations
        SET archived_at = now()
        WHERE id = :conversation_id
          AND archived_at IS NULL
        """
    ),
    {"conversation_id": "<conversation-uuid>"},
)

# Optional cascade archive in same migration/script.
op.execute(
    sa.text(
        """
        UPDATE messages
        SET archived_at = now()
        WHERE conversation_id = :conversation_id
          AND archived_at IS NULL
        """
    ),
    {"conversation_id": "<conversation-uuid>"},
)
op.execute(
    sa.text(
        """
        UPDATE files
        SET archived_at = now()
        WHERE conversation_id = :conversation_id
          AND archived_at IS NULL
        """
    ),
    {"conversation_id": "<conversation-uuid>"},
)
op.execute(
    sa.text(
        """
        UPDATE heartbeat_jobs
        SET archived_at = now()
        WHERE conversation_id = :conversation_id
          AND archived_at IS NULL
        """
    ),
    {"conversation_id": "<conversation-uuid>"},
)
```

```python
# Alembic downgrade() or recovery script example: restore the same conversation tree.
op.execute(
    sa.text(
        """
        UPDATE conversations
        SET archived_at = NULL
        WHERE id = :conversation_id
          AND archived_at IS NOT NULL
        """
    ),
    {"conversation_id": "<conversation-uuid>"},
)
op.execute(
    sa.text(
        """
        UPDATE messages
        SET archived_at = NULL
        WHERE conversation_id = :conversation_id
          AND archived_at IS NOT NULL
        """
    ),
    {"conversation_id": "<conversation-uuid>"},
)
op.execute(
    sa.text(
        """
        UPDATE files
        SET archived_at = NULL
        WHERE conversation_id = :conversation_id
          AND archived_at IS NOT NULL
        """
    ),
    {"conversation_id": "<conversation-uuid>"},
)
op.execute(
    sa.text(
        """
        UPDATE heartbeat_jobs
        SET archived_at = NULL
        WHERE conversation_id = :conversation_id
          AND archived_at IS NOT NULL
        """
    ),
    {"conversation_id": "<conversation-uuid>"},
)
```
