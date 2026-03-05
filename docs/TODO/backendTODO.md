# Backend TODO

## 0) Service Architecture and Bootstrap
- [x] Create FastAPI project for `codexchat_back` with modular domains: `auth`, `chat`, `codex`, `files`, `settings`, `admin`, `locks`. (completed 2026-03-05)
- [x] Create separate worker service `codexchat_worker` in same codebase/package (`jobs`, `heartbeat`, `scheduler`). (completed 2026-03-05)
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
- [ ] Implement cookie-based session auth with secure/httpOnly cookies.
- [ ] Add CSRF protection strategy for cookie-authenticated endpoints.
- [ ] Implement password hashing (Argon2id preferred).
- [ ] Implement login lockout counters (Redis preferred, DB fallback).
- [ ] Add generic auth error responses (no user enumeration).

## 3) Admin Bootstrap and User Management
- [ ] Implement startup bootstrap for first admin (env or CLI path).
- [ ] Implement CLI user creation command for SSH bootstrap (`create-user`).
- [ ] Disable public registration by default.
- [ ] Implement admin-only endpoints:
- [ ] `POST /api/admin/users` create user.
- [ ] `GET /api/admin/users` list users.
- [ ] `PATCH /api/admin/users/:id` update status/role/reset flags.
- [ ] Add forced password reset on first login for newly created users.

## 4) Conversation and Message Domain
- [ ] Implement `GET /api/conversations` list conversations.
- [ ] Implement `POST /api/conversations` create conversation.
- [ ] Implement `GET /api/conversations/:id` fetch conversation and messages.
- [ ] Implement `POST /api/conversations/:id/title` rename conversation.
- [ ] Implement soft-delete/archive flags for conversations/messages.
- [ ] Implement shared visibility model (all users can access all conversations/files).
- [ ] Add conversation activity timestamps updates on each turn.

## 5) WebSocket Messaging and Streaming
- [ ] Implement websocket auth/session check for `/ws`.
- [ ] Implement inbound events: `send_message`, `resume`.
- [ ] Implement outbound events: `assistant_delta`, `assistant_done`, `error`.
- [ ] Add websocket connection lifecycle handling (connect/disconnect/reconnect-safe state).
- [ ] Add error mapping from Codex/runtime failures to websocket error events.

## 6) Codex Bridge (API Service)
- [ ] Build Codex process runner using `codex app-server --listen stdio://`.
- [ ] Implement spawn-per-turn lifecycle:
- [ ] spawn process on send.
- [ ] stream output deltas.
- [ ] persist final output.
- [ ] terminate process after completion/error/timeout.
- [ ] Persist and reuse `codex_thread_id` per conversation.
- [ ] Add process timeout and cleanup guardrails.

## 7) Thread Locking and Concurrency
- [ ] Implement per-conversation lock acquisition before turn execution.
- [ ] If locked, reject send immediately with `thread busy` response (no FIFO queue).
- [ ] Add lock timeout + stale lock recovery.
- [ ] Expose lock/busy state to websocket/UI consumers.
- [ ] Add lock release in success, error, and timeout paths.

## 8) Files Domain (Local Storage Only)
- [ ] Implement upload endpoint: `POST /api/conversations/:id/files`.
- [ ] Store files on local disk under `UPLOADS_PATH`.
- [ ] Enforce user-configurable upload limit (default 15 MB).
- [ ] Record file metadata in DB and link via `message_files`.
- [ ] Implement download endpoint `GET /api/files/:id` with auth checks.
- [ ] Ensure attached file paths are included in turn payload sent to Codex.
- [ ] Ensure file references/paths are returned to frontend for message rendering.

## 9) Settings Domain
- [ ] Implement `GET /api/settings` and `PATCH /api/settings`.
- [ ] Store defaults: execution mode, upload limit, heartbeat defaults/cap, theme preference.
- [ ] Enforce product defaults:
- [ ] YOLO available to all users.
- [ ] heartbeat disabled by default.
- [ ] heartbeat cap default 10, optional unlimited.
- [ ] upload max default 15 MB.
- [ ] Include shared-workspace non-privacy warning flag/content.

## 10) Heartbeat Worker (Separate Service)
- [ ] Implement heartbeat job CRUD endpoints in API:
- [ ] `GET /api/heartbeat-jobs`
- [ ] `POST /api/heartbeat-jobs`
- [ ] `PATCH /api/heartbeat-jobs/:id`
- [ ] `DELETE /api/heartbeat-jobs/:id`
- [ ] Implement worker polling/scheduler loop in `codexchat_worker`.
- [ ] Enforce interval presets and minimum interval rules.
- [ ] Enforce defaults: disabled by default, max 10 jobs unless unlimited setting.
- [ ] For each run: read markdown file path, send as conversation turn, persist output.
- [ ] Persist run logs in `heartbeat_runs` with status and errors.

## 11) Search and Query Performance (MVP+)
- [ ] Implement conversation search endpoint: `GET /api/conversations/search?q=...`.
- [ ] Add indexed query strategy for title and message text.
- [ ] Return relevance-ordered results with pagination.

## 12) Safety and Warning Surfaces
- [ ] Add API-provided warning content for destructive operations.
- [ ] Add explicit warning payload for YOLO mode usage.
- [ ] Add non-privacy warning payload for shared VPS mode.
- [ ] Ensure warning metadata can be rendered in frontend settings and chat.

## 13) Integration and Manual Verification Checklist
- [ ] Verify login + lockout behavior end-to-end.
- [ ] Verify admin bootstrap and admin user management endpoints.
- [ ] Verify websocket streaming for normal conversation turns.
- [ ] Verify thread-busy reject behavior under concurrent sends.
- [ ] Verify uploads/downloads and path injection into Codex turns.
- [ ] Verify heartbeat worker runs independently from API responsiveness.
- [ ] Verify `/api` + `/ws` routing compatibility with Traefik single-domain setup.
