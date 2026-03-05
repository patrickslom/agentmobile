# Builder Loop

## Purpose
Repeatable execution loop for building this project task-by-task from TODO files.

Use this loop every run.

## Inputs
- `docs/TODO/frontendTODO.md`
- `docs/TODO/backendTODO.md`
- `docs/TODO/dbTODO.md`
- Current git repo with remote `origin`

## Loop (One Task Per Run)
1. Read all TODO files and select the next unchecked task (`- [ ]`) in priority order:
   1) `docs/TODO/dbTODO.md`
   2) `docs/TODO/backendTODO.md`
   3) `docs/TODO/frontendTODO.md`
2. Announce selected task to user with exact file + section + line context.
3. Ask user exactly 3 short questions before implementation.
4. Record assumptions from answers in the run log section (append at end of this file).
5. Implement only the selected task and tightly related required sub-work.
6. Run local validation for touched area:
   - lint/type checks (if available)
   - unit/integration command (if available)
   - build command (if available)
7. If validation fails, fix and re-run until pass or clearly blocked.
8. Update TODO item from `- [ ]` to `- [x]` with completion note/date.
9. Commit only files modified in this run with a task-specific message.
10. Push commit to `master` on GitHub (`origin master`).
11. Rebuild/restart containers on VPS:
   - `docker compose build`
   - `docker compose up -d`
12. Run smoke checks:
   - API health endpoint
   - web reachable
   - websocket route reachable (basic check)
13. Post run summary to user:
   - completed task
   - files changed
   - commit hash
   - container status
14. Stop after one completed task.

## Required Guardrails
- Do not start a new task in the same run after marking one complete.
- If repo has unrelated dirty changes, do not revert them and do not ask what to do; leave them unstaged and continue with only files you edited for the selected task.
- If blocked by missing secrets/infra, stop and report exact blocker.
- If push fails, do not mark task complete.
- If deploy/smoke checks fail, report and optionally rollback before stopping.

## Task Selection Rules
- Always pick the earliest unchecked task in the highest-priority TODO file.
- Do not skip tasks unless user explicitly approves skip.
- If task is too large, split into sub-tasks and add them before implementation.

## Definition of Done (Per Task)
A task is done only when all are true:
- code/docs updated
- validation run
- TODO checkbox updated
- commit created
- pushed to `master` with only run-modified files (unless user explicitly approved broader scope)
- containers rebuilt/restarted
- smoke checks passed

## Suggested Additions (Important)
Include these in every run even if not explicitly requested:
- Pre-run snapshot:
  - `git status`
  - `git rev-parse --short HEAD`
- Rollback point:
  - record previous commit hash before changes
- Deployment log:
  - keep `RUN_LOG.md` entry per run (task, commit, outcome)
- Safety gate:
  - require explicit user confirmation before destructive DB migrations
- Secrets gate:
  - never print sensitive env values in logs/output

## Standard Commands (Template)
```bash
# preflight
git status --short
git rev-parse --short HEAD

# implement task ...

# validate
# (project-specific commands)

# commit + push
git add <paths-you-edited>
git commit -m "feat: complete <todo-task-id>"
git push origin master

# deploy
docker compose build
docker compose up -d
```

## Run Log (Append Per Run)
- Date:
- Task completed:
- Questions asked:
- Assumptions:
- Validation commands/results:
- Commit: `64fd6c2` - feat(frontend): bootstrap Next.js app and deploy CodexChat frontend via existing Traefik network
- Push: `origin/master` updated successfully
- Deploy status:
- Smoke check status:
- Notes/blockers:

- Date: 2026-03-05
- Task completed: docs/TODO/frontendTODO.md :: 0) Project Bootstrap :: Add app shell layout with responsive viewport and safe-area handling.
- Questions asked:
  1) Should this app shell be implemented in `codexchat_front/app/layout.tsx` with a reusable wrapper component?
  2) Should safe-area support target `env(safe-area-inset-*)` for iOS-style notches with fallbacks to `0px`?
  3) Should I include only structural shell styling now (no auth/nav logic), keeping scope strictly to this checklist item?
- Assumptions:
  - User approved structural-only scope and no auth/nav behavior in this task.
  - App shell is implemented directly in `app/layout.tsx` with a simple wrapper + main content container.
  - Safe-area support uses `env(safe-area-inset-*)` variables with `0px` fallback values.
- Validation commands/results:
  - `cd codexchat_front && npm run lint` ✅
  - `cd codexchat_front && npm run build` ✅
- Commit:
- Push:
- Deploy status:
- Smoke check status:
- Notes/blockers:

- Date: 2026-03-05
- Task completed: docs/TODO/frontendTODO.md :: 0) Project Bootstrap :: Add global style tokens for black/white theme and dark mode variables.
- Questions asked:
  1) Should tokens be defined in `codexchat_front/app/globals.css` using CSS custom properties?
  2) Should we include only core semantic tokens now (`background`, `foreground`, `muted`, `border`, `accent`)?
  3) Should dark mode be wired via `prefers-color-scheme` with no manual toggle yet?
- Assumptions:
  - User approved all three questions.
  - This task is limited to global token definition and theme variable wiring only.
  - Dark mode behavior follows OS/browser preference only for now.
- Validation commands/results:
  - `cd codexchat_front && npm run lint` ✅
  - `cd codexchat_front && npm run build` ✅
- Commit: `76648af` - feat(frontend): add global black/white theme tokens with dark-mode variables
- Push: `origin/master` updated successfully
- Deploy status: `docker compose build` + `docker compose up -d` succeeded for `codexchat_front`.
- Smoke check status:
  - `https://todo.flounderboard.com/` ✅ (HTTP 200)
  - `https://todo.flounderboard.com/api/health` ⚠️ (HTTP 404; backend health endpoint not available yet)
  - `https://todo.flounderboard.com/ws` with upgrade headers ⚠️ (HTTP 404; websocket route not available yet)
- Notes/blockers:
  - Frontend-only run; backend routing endpoints are pending backend TODO implementation.

- Date: 2026-03-05
- Task completed: docs/TODO/frontendTODO.md :: 0) Project Bootstrap :: Create Next.js app with TypeScript and Tailwind in `codexchat_front`.
- Questions asked:
  1) Start with frontend bootstrap first despite default DB/backend priority?
  2) Scaffold `codexchat_front/` with Next.js App Router + Tailwind?
  3) Also handle HTTPS certificate in same run or frontend-only?
- Assumptions:
  - User approved frontend-first execution order for this run.
  - User approved Next.js + TypeScript + Tailwind scaffold.
  - Existing Traefik network is `n8n_default`; do not create a new network.
- Validation commands/results:
  - `cd codexchat_front && npm run lint` ✅
  - `cd codexchat_front && npm run build` ✅
- Commit:
- Push:
- Deploy status: `docker compose build` + `docker compose up -d` succeeded for `codexchat_front`.
- Smoke check status:
  - `https://todo.flounderboard.com` ✅ (HTTP 200)
  - `https://www.todo.flounderboard.com` ✅ (HTTP 200)
- Notes/blockers:
  - CodexChat primary production domains still require DNS alignment before LE certificate validation can complete on this VPS.

- Date: 2026-03-05
- Task completed: docs/TODO/frontendTODO.md :: 0) Project Bootstrap :: Set up base folder structure: `app/`, `components/`, `lib/`, `hooks/`, `types/`.
- Questions asked:
  1) Should folders be top-level in `codexchat_front/`?
  2) Add `.gitkeep` placeholders in empty folders?
  3) Add path aliases for these folders in `tsconfig.json`?
- Assumptions:
  - User confirmed all three questions.
  - Existing `app/` folder from Next.js scaffold remains as the app root.
  - Empty base folders should be tracked via `.gitkeep` placeholders.
- Validation commands/results:
- Commit:
- Push:
- Deploy status:
- Smoke check status:
- Notes/blockers:

- Date: 2026-03-05
- Task completed: docs/TODO/frontendTODO.md :: 0) Project Bootstrap :: Add API base URL and WebSocket URL environment wiring.
- Questions asked:
  1) Should I wire this as `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_WS_URL` in frontend env files?
  2) Should WebSocket default be derived from API URL when `NEXT_PUBLIC_WS_URL` is unset?
  3) Should I add a small typed helper in `lib/` for reading/validating these URLs at runtime?
- Assumptions:
  - User clarified preferred behavior is domain-driven routing: user provides a domain and frontend should target `<domain>/api` and `<domain>/ws`.
  - `NEXT_PUBLIC_APP_ORIGIN` is the primary frontend input, with optional overrides `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_WS_URL`.
  - Docker build wiring should pass public env values at build-time so Next.js client configuration is consistent in container builds.
- Validation commands/results:
  - `cd codexchat_front && npm run lint` ✅
  - `cd codexchat_front && npm run build` ✅
  - `docker compose config` ✅ (rendered successfully; warning observed when `APP_DOMAIN` is unset in shell env)
- Commit: `e91dee6` - feat(frontend): wire API and websocket URLs from app domain
- Push: `origin/master` updated successfully
- Deploy status:
  - `docker compose build` ✅
  - `docker compose up -d` ✅

- Date: 2026-03-05
- Task completed: docs/TODO/dbTODO.md :: 2) Auth and Session Support Tables
- Questions asked:
  1) Should `sessions.id` be UUID with `gen_random_uuid()` like existing core tables?
  2) Should session expiration use `expires_at TIMESTAMPTZ` plus `revoked_at TIMESTAMPTZ NULL` for explicit invalidation?
  3) For `auth_attempts.key`, do you want a single text key format with a unique index?
- Assumptions:
  - `sessions.id` uses UUID primary key with `gen_random_uuid()`.
  - Session rows include `token_hash` (opaque token hash), `created_at`, optional `last_seen_at`, `expires_at`, and nullable `revoked_at`.
  - `auth_attempts.key` is canonical/authoritative lookup with unique index.
  - `auth_attempts` also stores nullable `email` and `ip` fields for reporting/debug.
- Validation commands/results:
  - `cd codexchat_back && python3 -m compileall app alembic` ✅
  - `docker compose run --rm --build codexchat_back alembic upgrade head` ✅ (upgraded `20260305_02` -> `20260305_03`)
  - `docker compose run --rm codexchat_back alembic current` ✅ (`20260305_03 (head)`)
- Commit: `fd4f186` - feat(db): add sessions and auth_attempts schema for session auth fallback
- Push:
- Deploy status:
- Smoke check status:
- Notes/blockers:
- Smoke check status:
  - `https://todo.flounderboard.com/` ✅ (HTTP 200)
  - `https://todo.flounderboard.com/api/health` ⚠️ (HTTP 404; backend endpoint not implemented/routed yet)
  - `https://todo.flounderboard.com/ws` with upgrade headers ⚠️ (HTTP 404; websocket route not implemented/routed yet)
- Notes/blockers:
  - Frontend task completed and deployed; API/WS smoke checks remain expectedly unavailable until backend TODO items are implemented.

- Date: 2026-03-05
- Task completed: docs/TODO/frontendTODO.md :: 1) Routing and App Shell :: Create route: `/login`.
- Questions asked:
  1) Should `/login` be a public page that redirects to `/chat` if a session already exists?
  2) Should I include just the route/page scaffold now, or scaffold plus basic placeholder UI copy?
  3) Do you want `/login` implemented as `app/login/page.tsx` with server component default (no client hooks yet)?
- Assumptions:
  - User wants the login experience to lead into chat behavior, while this task remains scoped to creating the `/login` route only.
  - User requested scaffold plus basic UI now.
  - Server-component implementation is acceptable; session redirect behavior is implemented using conservative cookie-key checks until backend auth naming is finalized.
- Validation commands/results:
  - `cd codexchat_front && npm run lint` ✅
  - `cd codexchat_front && npm run build` ✅
- Commit:
- Push:
- Deploy status:
- Smoke check status:
- Notes/blockers:
  - `/chat` and conversation-history sidebar behavior are tracked by later frontend TODO items and were not implemented in this single-task run.

- Date: 2026-03-05
- Task completed: docs/TODO/dbTODO.md :: 1) Core Schema (Global Shared Model)
- Questions asked:
  1) Should IDs for these tables use `UUID` (instead of integer/bigint)?
  2) Should `role` columns be PostgreSQL `ENUM` types or plain `TEXT` with check constraints?
  3) Should `created_at/updated_at` use timezone-aware timestamps (`TIMESTAMPTZ`) with DB defaults (`now()`)?
- Assumptions:
  - IDs use UUID primary keys generated in DB via `gen_random_uuid()` (pgcrypto).
  - Role/status style fields use `TEXT` + `CHECK` constraints for MVP migration flexibility.
  - `created_at` and `updated_at` use `TIMESTAMPTZ NOT NULL DEFAULT now()`.
  - `updated_at` is maintained in DB via trigger (implemented for tables that include an `updated_at` column in this section).
- Validation commands/results:
  - `cd codexchat_back && python3 -m compileall app alembic` ✅
  - `docker compose run --rm --build codexchat_back alembic upgrade head` ✅ (upgraded `20260305_01` -> `20260305_02`)
  - `docker compose run --rm codexchat_back alembic current` ✅ (`20260305_02 (head)`)
- Commit: `db86e53` - feat(db): add core shared schema tables with UUID keys and timestamp triggers
- Push: `origin/master` updated successfully
- Deploy status:
  - `docker compose build` ✅
  - `docker compose up -d` ✅
- Smoke check status:
  - `https://todo.flounderboard.com/` ✅ (HTTP 200)
  - `https://todo.flounderboard.com/api/health` ✅ (HTTP 200)
  - `https://todo.flounderboard.com/ws` with websocket upgrade headers ⚠️ (HTTP 404; websocket endpoint pending backend websocket implementation)
- Notes/blockers:
  - Websocket upgrade route currently returns `404`; backend websocket feature work remains in backend TODO scope.

- Date: 2026-03-05
- Task completed: docs/TODO/dbTODO.md :: 0) Foundation and Tooling
- Questions asked:
  1) Should I implement this in the existing backend service at `codexchat_back` (SQLAlchemy + Alembic there)?
  2) For startup DB connectivity, do you want hard fail on app boot if DB is unreachable?
  3) Should I add a short DB workflow doc under `docs/` as part of the “baseline and versioning workflow docs” item?
- Assumptions:
  - User approved implementing DB foundation in `codexchat_back`.
  - API startup should fail fast when DB connectivity check fails.
  - Migration baseline/versioning workflow documentation is included in `docs/dbMigrations.md`.
- Validation commands/results:
  - `cd codexchat_back && python3 -m compileall app alembic` ✅
  - `cd /root/codexchat && docker compose config` ✅
- Commit:
- Push:
- Deploy status:
- Smoke check status:
- Notes/blockers:
  - Unrelated workspace changes existed and were intentionally excluded from staging/commit.

- Date: 2026-03-05
- Task completed: docs/TODO/backendTODO.md :: 0) Service Architecture and Bootstrap
- Questions asked:
  1) Should I scaffold both API and worker entrypoints now even if worker logic is just health + placeholder modules in this section?
  2) For logging, do you want JSON logs by default or readable text logs with request/conversation IDs?
  3) Should health endpoints be exactly `GET /api/health` for API and `GET /health` for worker service?
- Assumptions:
  - API and worker are scaffolded up front with worker placeholders in `jobs`, `heartbeat`, and `scheduler`.
  - Default logs are structured JSON with `LOG_PRETTY` env toggle for local human-readable output.
  - Health paths are implemented as `/api/health` (API) and `/health` (worker).
- Validation commands/results:
  - `cd codexchat_back && python3 -m compileall app alembic` ✅
  - `docker compose config` ✅
- Commit: `42b374f` - feat(backend): bootstrap modular api/worker services with shared config and structured logging
- Push: `origin/master` updated successfully
- Deploy status:
  - `docker compose build` ✅
  - `docker compose up -d` ✅
- Smoke check status:
  - `https://todo.flounderboard.com/` ✅ (HTTP 200)
  - `https://todo.flounderboard.com/api/health` ✅ (HTTP 200)
  - WebSocket handshake to `wss://todo.flounderboard.com/ws` ✅ (from `codexchat_back` container with Python `websockets`)
  - `codexchat_worker` health (`http://127.0.0.1:8001/health` inside container) ✅
- Notes/blockers:
  - Initial API/WS smoke briefly returned `502` during service restart; both passed after startup stabilization.

- Date: 2026-03-05
- Task completed: docs/TODO/backendTODO.md :: 1) API Surface and Routing Contract
- Questions asked:
  1) Should I enforce a single global API prefix by mounting all REST routers under `/api` (leaving non-API routes only for health/docs as needed)?
  2) For `/ws`, should authentication be optional for now (routing contract only) or require session validation immediately?
  3) For the JSON error envelope, should I use `{ "error": { "code", "message", "details", "request_id" } }` as the standard shape?
- Assumptions:
  - All business REST endpoints must remain under `/api`; non-business health probes can stay outside `/api`.
  - `/ws` must enforce authentication immediately during websocket upgrade and reject unauthorized clients.
  - Error envelopes must use stable `code`, always include `request_id`, and keep `details` consistently as an object.
  - `AUTH_INVALID`, `RATE_LIMITED`, `VALIDATION_ERROR`, `NOT_FOUND`, and `INTERNAL` are treated as stable baseline codes.
- Validation commands/results:
  - `cd codexchat_back && python3 -m compileall app` ✅
  - `cd codexchat_back && python3 -m compileall alembic` ✅
- Commit:
  - `f018029` - feat(backend): enforce /api and authenticated /ws contract with standard errors
  - `c57126d` - fix(backend): apply error envelope to framework 404/405 responses
- Push: `origin/master` updated successfully (to `c57126d`)
- Deploy status:
  - `docker compose build` ✅
  - `docker compose up -d` ✅
- Smoke check status:
  - `https://todo.flounderboard.com/` ✅ (HTTP 200)
  - `https://todo.flounderboard.com/api/health` ✅ (HTTP 200)
  - `https://todo.flounderboard.com/api/does-not-exist` ✅ (HTTP 404 with standard JSON error envelope including `request_id`)
  - `wss://todo.flounderboard.com/ws` ✅ reachable and auth-enforced (`HTTP 403` on unauthenticated upgrade)
- Notes/blockers:
  - First smoke attempt briefly returned `502` while Traefik/backend routing converged after container recreation; subsequent retries were stable and passing.
  - Websocket auth in this section uses a transitional cookie format (`codexchat_session` as user UUID) until full signed session persistence is implemented in section 2.
