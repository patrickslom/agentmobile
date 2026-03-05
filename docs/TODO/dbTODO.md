# Database TODO

## 0) Foundation and Tooling
- [ ] Set up SQLAlchemy models and DB session management for Postgres.
- [ ] Set up Alembic migration environment.
- [ ] Create initial migration baseline and versioning workflow docs.
- [ ] Add DB config validation from environment (`DATABASE_URL`).
- [ ] Add startup DB connectivity check.

## 1) Core Schema (Global Shared Model)
- [ ] Create `users` table:
- [ ] `id`, `email` (unique), `password_hash`, `role`, `is_active`, `force_password_reset`, `created_at`, `updated_at`.
- [ ] Create `conversations` table (global shared):
- [ ] `id`, `title`, `codex_thread_id`, `created_at`, `updated_at`, `archived_at`.
- [ ] Create `messages` table:
- [ ] `id`, `conversation_id`, `role`, `content`, `created_at`, `archived_at`.
- [ ] Create `files` table:
- [ ] `id`, `conversation_id`, `original_name`, `storage_path`, `mime_type`, `size_bytes`, `created_at`, `archived_at`.
- [ ] Create `message_files` join table:
- [ ] `id`, `message_id`, `file_id`, `created_at`.

## 2) Auth and Session Support Tables
- [ ] Create `sessions` table for cookie auth sessions.
- [ ] Add session indexes for lookup and expiration cleanup.
- [ ] Create `auth_attempts` table for lockout fallback when Redis is absent.
- [ ] Add fields: `key`, `fail_count`, `ban_level`, `ban_until`, `last_failed_at`, `updated_at`.

## 3) Settings and Admin Tables
- [ ] Create `settings` table (global app settings + defaults).
- [ ] Include fields for:
- [ ] execution mode defaults
- [ ] upload size limit default (`15 MB` baseline)
- [ ] heartbeat defaults (disabled baseline)
- [ ] heartbeat cap default (`10`) and unlimited flag
- [ ] theme default (light)
- [ ] Create any needed `audit_logs` table for admin actions (create user, disable user, password reset).

## 4) Heartbeat Schema
- [ ] Create `heartbeat_jobs` table:
- [ ] `id`, `conversation_id`, `instruction_file_path`, `enabled`, `created_at`, `updated_at`, `archived_at`.
- [ ] Create `heartbeat_schedules` table:
- [ ] `id`, `heartbeat_job_id`, `interval_minutes`, `next_run_at`, `last_run_at`, `created_at`, `updated_at`.
- [ ] Create `heartbeat_runs` table:
- [ ] `id`, `heartbeat_job_id`, `started_at`, `finished_at`, `status`, `error_text`, `created_at`.

## 5) Concurrency and Locks Schema
- [ ] Create `conversation_locks` table (or equivalent lock record) for per-thread active run protection.
- [ ] Add fields: `conversation_id` (unique), `locked_by`, `locked_at`, `expires_at`.
- [ ] Add stale-lock recovery strategy fields and migration notes.

## 6) Archive/Soft Delete Behavior
- [ ] Standardize `archived_at` nullable timestamp semantics across archivable tables.
- [ ] Ensure default queries exclude archived rows.
- [ ] Add admin/archive queries that can include archived rows.
- [ ] Add recover/restore migration-safe workflow notes.

## 7) Indexing and Performance
- [ ] Add index on `conversations.updated_at` for sidebar ordering.
- [ ] Add index on `messages.conversation_id, created_at` for timeline fetch.
- [ ] Add index on `files.conversation_id, created_at` for attachment retrieval.
- [ ] Add index on `sessions.expires_at` for cleanup jobs.
- [ ] Add index on `conversation_locks.expires_at` for stale lock scanning.
- [ ] Add text search indexes for MVP+ conversation search (title/content).

## 8) Constraints and Data Integrity
- [ ] Add foreign keys for conversation/message/file relations.
- [ ] Add cascade/archive behavior policy (avoid hard cascade delete in MVP).
- [ ] Add check constraints for role enums (`user`, `admin`) and message roles.
- [ ] Add uniqueness constraints where required (`users.email`, conversation lock uniqueness).
- [ ] Add size/value constraints for configured limits where appropriate.

## 9) Seed and Bootstrap Data
- [ ] Add migration/seed path for first admin user creation support.
- [ ] Add default settings seed row with product defaults.
- [ ] Ensure idempotent seed behavior.

## 10) Operational Jobs and Maintenance
- [ ] Add periodic cleanup strategy for expired sessions.
- [ ] Add periodic cleanup strategy for stale locks.
- [ ] Add archival maintenance notes for old messages/files.
- [ ] Add DB backup/restore runbook notes for production.

## 11) Alembic Migration Hygiene
- [ ] Split migrations into logical phases (core/auth/settings/heartbeat/locks/indexes).
- [ ] Ensure every migration has tested downgrade path where safe.
- [ ] Add migration naming conventions and review checklist.
- [ ] Add startup guard to fail fast if DB revision is behind.

## 12) Manual Verification Checklist
- [ ] Verify fresh migration apply on empty DB.
- [ ] Verify migration upgrade path from prior revisions.
- [ ] Verify archived records are hidden by default queries.
- [ ] Verify restore-from-archive flow works for conversation/message/file records.
- [ ] Verify lock table behavior under concurrent send attempts.
- [ ] Verify heartbeat tables populate correctly during runs.
- [ ] Verify search-related indexes exist and are used for target queries.
