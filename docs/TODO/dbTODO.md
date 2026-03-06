# Database TODO

## 0) Foundation and Tooling
- [x] Set up SQLAlchemy models and DB session management for Postgres. (completed 2026-03-05)
- [x] Set up Alembic migration environment. (completed 2026-03-05)
- [x] Create initial migration baseline and versioning workflow docs. (completed 2026-03-05)
- [x] Add DB config validation from environment (`DATABASE_URL`). (completed 2026-03-05)
- [x] Add startup DB connectivity check. (completed 2026-03-05)

## 1) Core Schema (Global Shared Model)
- [x] Create `users` table: (completed 2026-03-05)
- [x] `id`, `email` (unique), `password_hash`, `role`, `is_active`, `force_password_reset`, `created_at`, `updated_at`. (completed 2026-03-05)
- [x] Create `conversations` table (global shared): (completed 2026-03-05)
- [x] `id`, `title`, `codex_thread_id`, `created_at`, `updated_at`, `archived_at`. (completed 2026-03-05)
- [x] Create `messages` table: (completed 2026-03-05)
- [x] `id`, `conversation_id`, `role`, `content`, `created_at`, `archived_at`. (completed 2026-03-05)
- [x] Create `files` table: (completed 2026-03-05)
- [x] `id`, `conversation_id`, `original_name`, `storage_path`, `mime_type`, `size_bytes`, `created_at`, `archived_at`. (completed 2026-03-05)
- [x] Create `message_files` join table: (completed 2026-03-05)
- [x] `id`, `message_id`, `file_id`, `created_at`. (completed 2026-03-05)

## 2) Auth and Session Support Tables
- [x] Create `sessions` table for cookie auth sessions. (completed 2026-03-05)
- [x] Add session indexes for lookup and expiration cleanup. (completed 2026-03-05)
- [x] Create `auth_attempts` table for lockout fallback when Redis is absent. (completed 2026-03-05)
- [x] Add fields: `key`, `fail_count`, `ban_level`, `ban_until`, `last_failed_at`, `updated_at`. (completed 2026-03-05)

## 3) Settings and Admin Tables
- [x] Create `settings` table (global app settings + defaults). (completed 2026-03-05)
- [x] Include fields for: (completed 2026-03-05)
- [x] execution mode defaults (completed 2026-03-05)
- [x] upload size limit default (`15 MB` baseline) (completed 2026-03-05)
- [x] heartbeat defaults (disabled baseline) (completed 2026-03-05)
- [x] heartbeat cap default (`10`) and unlimited flag (completed 2026-03-05)
- [x] theme default (light) (completed 2026-03-05)
- [x] Create any needed `audit_logs` table for admin actions (create user, disable user, password reset). (completed 2026-03-05)

## 4) Heartbeat Schema
- [x] Create `heartbeat_jobs` table: (completed 2026-03-05)
- [x] `id`, `conversation_id`, `instruction_file_path`, `enabled`, `created_at`, `updated_at`, `archived_at`. (completed 2026-03-05)
- [x] Create `heartbeat_schedules` table: (completed 2026-03-05)
- [x] `id`, `heartbeat_job_id`, `interval_minutes`, `next_run_at`, `last_run_at`, `created_at`, `updated_at`. (completed 2026-03-05)
- [x] Create `heartbeat_runs` table: (completed 2026-03-05)
- [x] `id`, `heartbeat_job_id`, `started_at`, `finished_at`, `status`, `error_text`, `created_at`. (completed 2026-03-05)

## 5) Concurrency and Locks Schema
- [x] Create `conversation_locks` table (or equivalent lock record) for per-thread active run protection. (completed 2026-03-05)
- [x] Add fields: `conversation_id` (unique), `locked_by`, `locked_at`, `expires_at`. (completed 2026-03-05)
- [x] Add stale-lock recovery strategy fields and migration notes. (completed 2026-03-05)

## 6) Archive/Soft Delete Behavior
- [x] Standardize `archived_at` nullable timestamp semantics across archivable tables. (completed 2026-03-05)
- [x] Ensure default queries exclude archived rows. (completed 2026-03-05)
- [x] Add admin/archive queries that can include archived rows. (completed 2026-03-05)
- [x] Add recover/restore migration-safe workflow notes. (completed 2026-03-05)

## 7) Indexing and Performance
- [x] Add index on `conversations.updated_at` for sidebar ordering. (completed 2026-03-05)
- [x] Add index on `messages.conversation_id, created_at` for timeline fetch. (completed 2026-03-05)
- [x] Add index on `files.conversation_id, created_at` for attachment retrieval. (completed 2026-03-05)
- [x] Add index on `sessions.expires_at` for cleanup jobs. (completed 2026-03-05)
- [x] Add index on `conversation_locks.expires_at` for stale lock scanning. (completed 2026-03-05)
- [x] Add text search indexes for MVP+ conversation search (title/content). (completed 2026-03-05)

## 8) Constraints and Data Integrity
- [x] Add foreign keys for conversation/message/file relations. (completed 2026-03-05)
- [x] Add cascade/archive behavior policy (avoid hard cascade delete in MVP). (completed 2026-03-05)
- [x] Add check constraints for role enums (`user`, `admin`) and message roles. (completed 2026-03-05)
- [x] Add uniqueness constraints where required (`users.email`, conversation lock uniqueness). (completed 2026-03-05)
- [x] Add size/value constraints for configured limits where appropriate. (completed 2026-03-05)

## 9) Seed and Bootstrap Data
- [x] Add migration/seed path for first admin user creation support. (completed 2026-03-05)
- [x] Add default settings seed row with product defaults. (completed 2026-03-05)
- [x] Ensure idempotent seed behavior. (completed 2026-03-05)

## 10) Operational Jobs and Maintenance
- [x] Add periodic cleanup strategy for expired sessions. (completed 2026-03-05)
- [x] Add periodic cleanup strategy for stale locks. (completed 2026-03-05)
- [x] Add archival maintenance notes for old messages/files. (completed 2026-03-05)
- [x] Add DB backup/restore runbook notes for production. (completed 2026-03-05)

## 11) Alembic Migration Hygiene
- [x] Split migrations into logical phases (core/auth/settings/heartbeat/locks/indexes). (completed 2026-03-05)
- [x] Ensure every migration has tested downgrade path where safe. (completed 2026-03-05)
- [x] Add migration naming conventions and review checklist. (completed 2026-03-05)
- [x] Add startup guard to fail fast if DB revision is behind. (completed 2026-03-05)

## 12) Manual Verification Checklist
- [x] Verify fresh migration apply on empty DB. (completed 2026-03-05)
- [x] Verify migration upgrade path from prior revisions. (completed 2026-03-05)
- [x] Verify archived records are hidden by default queries. (completed 2026-03-05)
- [x] Verify restore-from-archive flow works for conversation/message/file records. (completed 2026-03-05)
- [x] Verify lock table behavior under concurrent send attempts. (completed 2026-03-05)
- [x] Verify heartbeat tables populate correctly during runs. (completed 2026-03-05)
- [x] Verify search-related indexes exist and are used for target queries. (completed 2026-03-05)
