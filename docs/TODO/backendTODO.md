# Backend TODO

## 0) Service Architecture and Bootstrap
- [x] Create FastAPI project for `backend` with modular domains: `auth`, `chat`, `codex`, `files`, `settings`, `admin`, `locks`. (completed 2026-03-05)
- [x] Create separate worker service `worker` in same codebase/package (`jobs`, `heartbeat`, `scheduler`). (completed 2026-03-05)
- [x] Add shared config module for env loading and validation. (completed 2026-03-05)
- [x] Add health endpoints for API and worker. (completed 2026-03-05)
- [x] Add logging setup with request IDs and conversation IDs. (completed 2026-03-05)

## 1) API Surface and Routing Contract
- [x] Implement API prefix routing under `/api`. (completed 2026-03-05)
- [x] Implement websocket endpoint at `/ws`. (completed 2026-03-05)
- [x] Ensure same-domain contract: `/` frontend, `/api/*` backend, `/ws` backend. (completed 2026-03-05)
- [x] Add consistent JSON error envelope format. (completed 2026-03-05)
- [x] Add OpenAPI tags grouped by domain. (completed 2026-03-05)

## 2) Core Security and Sessions
- [x] Implement cookie-based session auth with secure/httpOnly cookies. (completed 2026-03-05)
- [x] Add CSRF protection strategy for cookie-authenticated endpoints. (completed 2026-03-05)
- [x] Implement password hashing (Argon2id preferred). (completed 2026-03-05)
- [x] Implement login lockout counters (Redis preferred, DB fallback). (completed 2026-03-05)
- [x] Add generic auth error responses (no user enumeration). (completed 2026-03-05)

## 3) Admin Bootstrap and User Management
- [x] Implement startup bootstrap for first admin (env or CLI path). (completed 2026-03-05)
- [x] Implement CLI user creation command for SSH bootstrap (`create-user`). (completed 2026-03-05)
- [x] Disable public registration by default. (completed 2026-03-05)
- [x] Implement admin-only endpoints: (completed 2026-03-05)
- [x] `POST /api/admin/users` create user. (completed 2026-03-05)
- [x] `GET /api/admin/users` list users. (completed 2026-03-05)
- [x] `PATCH /api/admin/users/:id` update status/role/reset flags. (completed 2026-03-05)
- [x] `POST /api/admin/users/:id/temporary-password` reset with generated temporary password and revoke active sessions. (completed 2026-03-06)
- [x] Add forced password reset on first login for newly created users. (completed 2026-03-05)

## 4) Conversation and Message Domain
- [x] Implement `GET /api/conversations` list conversations. (completed 2026-03-06)
- [x] Implement `POST /api/conversations` create conversation. (completed 2026-03-06)
- [x] Implement `GET /api/conversations/:id` fetch conversation and messages. (completed 2026-03-06)
- [x] Implement `POST /api/conversations/:id/title` rename conversation. (completed 2026-03-06)
- [x] Implement soft-delete/archive flags for conversations/messages. (completed 2026-03-06)
- [x] Implement shared visibility model (all users can access all conversations/files). (completed 2026-03-06)
- [x] Add conversation activity timestamps updates on each turn. (completed 2026-03-06)

## 5) WebSocket Messaging and Streaming
- [x] Implement websocket auth/session check for `/ws`. (completed 2026-03-06)
- [x] Implement inbound events: `send_message`, `resume`. (completed 2026-03-06)
- [x] Implement outbound events: `assistant_delta`, `assistant_done`, `error`. (completed 2026-03-06)
- [x] Add websocket connection lifecycle handling (connect/disconnect/reconnect-safe state). (completed 2026-03-06)
- [x] Add error mapping from Codex/runtime failures to websocket error events. (completed 2026-03-06)

## 6) Codex Bridge (API Service)
- [x] Build Codex process runner using `codex app-server --listen stdio://`. (completed 2026-03-06)
- [x] Implement spawn-per-turn lifecycle: (completed 2026-03-06)
- [x] spawn process on send. (completed 2026-03-06)
- [x] stream output deltas. (completed 2026-03-06)
- [x] persist final output. (completed 2026-03-06)
- [x] terminate process after completion/error/timeout. (completed 2026-03-06)
- [x] Persist and reuse `codex_thread_id` per conversation. (completed 2026-03-06)
- [x] Add process timeout and cleanup guardrails. (completed 2026-03-06)

## 7) Thread Locking and Concurrency
- [x] Implement per-conversation lock acquisition before turn execution. (completed 2026-03-06)
- [x] If locked, reject send immediately with `thread busy` response (no FIFO queue). (completed 2026-03-06)
- [x] Add lock timeout + stale lock recovery. (completed 2026-03-06)
- [x] Expose lock/busy state to websocket/UI consumers. (completed 2026-03-06)
- [x] Add lock release in success, error, and timeout paths. (completed 2026-03-06)

## 8) Files Domain (Local Storage Only)
- [x] Implement upload endpoint: `POST /api/conversations/:id/files`. (completed 2026-03-06)
- [x] Store files on local disk under `UPLOADS_PATH`. (completed 2026-03-06)
- [x] Enforce user-configurable upload limit (default 15 MB). (completed 2026-03-06)
- [x] Record file metadata in DB and link via `message_files`. (completed 2026-03-06)
- [x] Implement download endpoint `GET /api/files/:id` with auth checks. (completed 2026-03-06)
- [x] Ensure attached file paths are included in turn payload sent to Codex. (completed 2026-03-06)
- [x] Ensure file references/paths are returned to frontend for message rendering. (completed 2026-03-06)

## 9) Settings Domain
- [x] Implement `GET /api/settings` and `PATCH /api/settings`. (completed 2026-03-06)
- [x] Store defaults: execution mode, upload limit, heartbeat defaults/cap, theme preference. (completed 2026-03-06)
- [x] Enforce product defaults: (completed 2026-03-06)
- [x] YOLO available to all users. (completed 2026-03-06)
- [x] heartbeat disabled by default. (completed 2026-03-06)
- [x] heartbeat cap default 10, optional unlimited. (completed 2026-03-06)
- [x] upload max default 15 MB. (completed 2026-03-06)
- [x] Include shared-workspace non-privacy warning flag/content. (completed 2026-03-06)

## 10) Heartbeat Worker (Separate Service)
- [x] Implement heartbeat job CRUD endpoints in API: (completed 2026-03-06)
- [x] `GET /api/heartbeat-jobs` (completed 2026-03-06)
- [x] `POST /api/heartbeat-jobs` (completed 2026-03-06)
- [x] `PATCH /api/heartbeat-jobs/:id` (completed 2026-03-06)
- [x] `DELETE /api/heartbeat-jobs/:id` (completed 2026-03-06)
- [x] Implement worker polling/scheduler loop in `worker`. (completed 2026-03-06)
- [x] Enforce interval presets and minimum interval rules. (completed 2026-03-06)
- [x] Enforce defaults: disabled by default, max 10 jobs unless unlimited setting. (completed 2026-03-06)
- [x] For each run: read markdown file path, send as conversation turn, persist output. (completed 2026-03-06)
- [x] Persist run logs in `heartbeat_runs` with status and errors. (completed 2026-03-06)

## 11) Search and Query Performance (MVP+)
- [x] Implement conversation search endpoint: `GET /api/conversations/search?q=...`. (completed 2026-03-06)
- [x] Add indexed query strategy for title and message text. (completed 2026-03-06)
- [x] Return relevance-ordered results with pagination. (completed 2026-03-06)

## 12) Safety and Warning Surfaces
- [x] Add API-provided warning content for destructive operations. (completed 2026-03-06)
- [x] Add explicit warning payload for YOLO mode usage. (completed 2026-03-06)
- [x] Add non-privacy warning payload for shared VPS mode. (completed 2026-03-06)
- [x] Ensure warning metadata can be rendered in frontend settings and chat. (completed 2026-03-06)

## 13) Integration and Manual Verification Checklist
- [x] Verify login + lockout behavior end-to-end. (completed 2026-03-06; CLI + browser login/lockout flow verified)
- [x] Verify admin bootstrap and admin user management endpoints. (completed 2026-03-12 per user confirmation of prior completion)
- [x] Verify websocket streaming for normal conversation turns. (completed 2026-03-12 per user confirmation of prior completion)
- [x] Verify thread-busy reject behavior under concurrent sends. (completed 2026-03-12 per user confirmation of prior completion)
- [x] Verify uploads/downloads and path injection into Codex turns. (completed 2026-03-12 per user confirmation of prior completion)
- [x] Verify heartbeat worker runs independently from API responsiveness. (completed 2026-03-06; heartbeat run observed while repeated `/api/health` checks remained `200`)
- [x] Verify `/api` + `/ws` routing compatibility with Traefik single-domain setup. (completed 2026-03-06; `/api/health` returned `200`; unauthenticated `/ws` upgrade returned `403`)
