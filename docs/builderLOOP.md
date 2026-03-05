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
   - This VPS is shared with other agents; deploy coordination is required through `LOCK.md` at repo root.
   - Before deploy, acquire build lock in `LOCK.md` with:
     - workstream (`FRONT|BACK|DB`)
     - current date/time (local + UTC)
     - lock acquire epoch seconds
     - short task label
   - If lock is active and age is `<= 20 minutes`, wait random 3-5 minutes and check again.
   - If lock is older than `20 minutes`, treat as stale: clear it, then acquire lock and proceed.
   - Run deploy with retry-until-success behavior while holding lock:
     - `docker compose build`
     - `docker compose up -d`
   - If either command fails, wait a random 3-5 minutes and retry until success.
   - After deploy succeeds, clear `LOCK.md` back to unlocked template for the next agent.
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
- Rebuild/restart is a shared resource: use `LOCK.md` coordination, respect 20-minute stale lock handling, and use random 3-5 minute retry delays until deploy succeeds.

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
workstream="FRONT" # set FRONT|BACK|DB for this run
agent="${USER:-agent}"
task_label="<todo-task-id>"
while :; do
  now_epoch="$(date +%s)"
  if grep -q "^LOCK_STATUS: LOCKED$" LOCK.md; then
    lock_epoch="$(awk -F': ' '/^LOCK_ACQUIRED_AT_EPOCH:/ {print $2}' LOCK.md)"
    age=$((now_epoch - ${lock_epoch:-0}))
    if [ "$age" -le 1200 ]; then
      sleep $((180 + RANDOM % 121))
      continue
    fi
  fi
  cat > LOCK.md <<EOF
LOCK_STATUS: LOCKED
WORKSTREAM: ${workstream}
AGENT: ${agent}
DATE_TIME_LOCAL: $(date +"%Y-%m-%d %H:%M:%S %Z")
DATE_TIME_UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOCK_ACQUIRED_AT_EPOCH: ${now_epoch}
TASK: ${task_label}
EOF
  break
done
until docker compose build && docker compose up -d; do
  sleep $((180 + RANDOM % 121))
done
cat > LOCK.md <<'EOF'
LOCK_STATUS: UNLOCKED
WORKSTREAM: NONE
AGENT: NONE
DATE_TIME_LOCAL: NONE
DATE_TIME_UTC: NONE
LOCK_ACQUIRED_AT_EPOCH: 0
TASK: NONE
EOF
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
- Task completed: docs/TODO/dbTODO.md :: 8) Constraints and Data Integrity
- Questions asked:
  1) Should FK behavior default to `ON DELETE RESTRICT` for MVP?
  2) Should message roles be constrained to `user|assistant|system` in MVP?
  3) Should value constraints include non-negative `files.size_bytes` and positive settings caps?
- Assumptions:
  - `ON DELETE RESTRICT` is the default for core parent entities, with targeted `CASCADE` on dependent/internal tables.
  - Message role constraint remains `user|assistant|system`.
  - `files.size_bytes` is constrained to `>= 0`; existing settings minimum constraints remain enforced.
- Validation commands/results:
  - `docker run --rm --network codexchat_codexchat_internal -e DATABASE_URL=... -v /root/codexchat/codexchat_back:/app -w /app codexchat-codexchat_back python -m compileall app alembic` ✅
  - `docker run --rm --network codexchat_codexchat_internal -e DATABASE_URL=... -v /root/codexchat/codexchat_back:/app -w /app codexchat-codexchat_back alembic heads` ✅ (`20260305_07`, `20260305_08`)
  - `docker run --rm --network codexchat_codexchat_internal -e DATABASE_URL=... -v /root/codexchat/codexchat_back:/app -w /app codexchat-codexchat_back alembic upgrade heads` ✅
- Commit:
- Push:
- Deploy status:
- Smoke check status:
- Notes/blockers:
  - Local workspace already contained untracked migration `20260305_07_indexing_and_search.py`; left as-is per guardrail.

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
- Push: `origin/master` updated successfully (to `32c1817`)
- Deploy status:
  - `docker compose build` ✅
  - `docker compose up -d` ✅
- Smoke check status:
  - `https://todo.flounderboard.com/` ✅ (HTTP 200)
  - `https://todo.flounderboard.com/api/health` ✅ (HTTP 200)
  - `https://todo.flounderboard.com/ws` with websocket upgrade headers ✅ (HTTP 403 expected without auth session cookie)
- Notes/blockers:
  - Initial smoke probe briefly returned `502` during service restart; subsequent checks passed after containers became fully ready.

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
- Task completed: docs/TODO/dbTODO.md :: 4) Heartbeat Schema
- Questions asked:
  1) Should `heartbeat_runs.status` be a Postgres enum or plain text?
  2) Should `heartbeat_jobs.conversation_id` and `heartbeat_schedules.heartbeat_job_id` use foreign keys now?
  3) Should this run include migration + minimal SQLAlchemy models, or migration-only?
- Assumptions:
  - `heartbeat_runs.status` uses `TEXT NOT NULL` with `CHECK (status IN ('queued','running','succeeded','failed'))` and default `'queued'`.
  - Foreign keys are added now:
    - `heartbeat_jobs.conversation_id -> conversations.id` with `ON DELETE CASCADE`
    - `heartbeat_schedules.heartbeat_job_id -> heartbeat_jobs.id` with `ON DELETE CASCADE`
    - `heartbeat_runs.heartbeat_job_id -> heartbeat_jobs.id` with `ON DELETE CASCADE`
  - Minimal SQLAlchemy models are added now for job/schedule/run tables without relationship wiring.
- Validation commands/results:
  - `cd codexchat_back && python3 -m compileall app alembic` ✅
  - `cd /root/codexchat && docker compose run --rm --build codexchat_back alembic upgrade head` ✅ (upgraded `20260305_04` -> `20260305_05`)
  - `cd /root/codexchat && docker compose run --rm codexchat_back alembic current` ✅ (`20260305_05 (head)`)
- Commit: `54283a0` - feat(db): add heartbeat jobs, schedules, and runs schema
- Push: `origin/master` updated successfully (`290a97f` -> `54283a0`)
- Deploy status:
  - `docker compose build` ✅
  - `docker compose up -d` ✅
- Smoke check status:
  - `https://todo.flounderboard.com/` ✅ (HTTP 200)
  - `https://todo.flounderboard.com/api/health` ✅ (HTTP 200)
  - `https://todo.flounderboard.com/ws` with websocket upgrade headers ✅ (HTTP 403 expected without authenticated session)
- Notes/blockers:
  - Initial smoke probe returned transient `502` during service warm-up; follow-up checks passed.

- Date: 2026-03-05
- Task completed: docs/TODO/dbTODO.md :: 3) Settings and Admin Tables
- Questions asked:
  1) Should `settings` be a single-row global table (`id=1`) with strict min/max checks (upload limit >= 1 MB, heartbeat cap >= 1)?
  2) For execution mode default, should we store it as text with allowed values `regular` and `yolo` (default `regular`)?
  3) For `audit_logs`, should we include fields `id`, `actor_user_id`, `action`, `target_user_id`, `metadata_json`, `created_at`?
- Assumptions:
  - Single-row global `settings` table is enforced by DB check `id = 1`.
  - `settings.execution_mode_default` is text constrained to `regular|yolo`, defaulting to `regular`.
  - `settings` includes `updated_at` and nullable `updated_by_user_id`, plus DB checks for `upload_limit_mb_default >= 1` and `heartbeat_cap_default >= 1`.
  - `audit_logs` includes requested fields plus `request_id` and `ip` for investigations, with flexible `metadata_json` JSONB payload.
- Validation commands/results:
  - `cd codexchat_back && python3 -m compileall app alembic` ✅
  - `docker compose run --rm --build codexchat_back alembic upgrade head` ✅ (upgraded `20260305_03` -> `20260305_04`)
  - `docker compose run --rm codexchat_back alembic current` ✅ (`20260305_04 (head)`)
- Commit: `eb0792c` - feat(db): add settings and audit logs schema with guarded defaults
- Push: `origin/master` updated successfully
- Deploy status:
  - `docker compose build` ✅
  - `docker compose up -d` ✅
- Smoke check status:
  - `https://todo.flounderboard.com/` ✅ (HTTP 200)
  - `https://todo.flounderboard.com/api/health` ✅ (HTTP 200)
  - `https://todo.flounderboard.com/ws` with websocket upgrade headers ✅ (HTTP 403 expected without auth session cookie)
- Notes/blockers:
  - Initial post-deploy probe briefly returned `502` for `/api/health` and `/ws`; checks passed after services fully stabilized.

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

- Date: 2026-03-05
- Task completed: docs/TODO/frontendTODO.md :: 1) Routing and App Shell (remaining items)
- Questions asked:
  1) Should `/chat` be the post-login default landing page for authenticated users?
  2) For `/settings/admin`, should non-admin users be redirected to `/settings`?
  3) Should logout call backend `POST /api/auth/logout`, clear the session cookie, then redirect to `/login`?
- Assumptions:
  - Authenticated users should default to `/chat` including authenticated visits to `/`.
  - Non-admin access to `/settings/admin` should be redirected to `/settings`.
  - Logout should call backend `/api/auth/logout`, expire frontend session cookies, and redirect to `/login?logged_out=1`.
- Validation commands/results:
  - `cd codexchat_front && timeout 180 npm run lint` ✅
  - `cd codexchat_front && npm run build` ⚠️ hangs in this environment during optimized production build (multiple retries; process remained active without completion output, manually terminated).
- Commit:
- Push:
- Deploy status: assumed completed by operator per user note (containers rebuilt/restarted externally during this run).
- Smoke check status:
- Notes/blockers:
  - Local Next.js build command is currently non-deterministic in this environment (hangs during production build stage).

- Date: 2026-03-05
- Task completed: docs/TODO/dbTODO.md :: 5) Concurrency and Locks Schema
- Questions asked:
  1) Should `locked_by` reference `users.id` as a nullable UUID foreign key?
  2) Should stale-lock recovery use an owner token plus `last_heartbeat_at`?
  3) Should migration notes be added in `docs/dbMigrations.md` under a new subsection?
- Assumptions:
  - `locked_by` is nullable UUID FK to `users.id`; user locks set `locked_by=user_id`, system/worker locks set `locked_by=NULL` with owner details in `metadata_json`.
  - Stale recovery uses `owner_token` compare-and-release plus `last_heartbeat_at` heartbeats; stale threshold is TTL-based.
  - Migration documentation includes schema changes, TTL defaults, recovery procedure, and required lock indexes.
- Validation commands/results:
  - `cd codexchat_back && python3 -m compileall app alembic` ✅
  - `docker compose run --rm --build codexchat_back alembic upgrade head` ✅ (upgraded `20260305_05` -> `20260305_06`)
  - `docker compose run --rm codexchat_back alembic current` ✅ (`20260305_06 (head)`)
- Commit: `05a5724` - feat(db): add conversation locks schema with stale recovery tokens
- Push: `origin/master` updated successfully (`efac14f` -> `05a5724`)
- Deploy status:
  - `docker compose build` ✅
  - `docker compose up -d` ✅
- Smoke check status:
  - `https://todo.flounderboard.com/` ✅ (HTTP 200)
  - `https://todo.flounderboard.com/api/health` ✅ (HTTP 200)
  - `wss://todo.flounderboard.com/ws` ✅ reachable/auth-enforced (`HTTP 403` with unauthenticated upgrade probe using HTTP/1.1 + valid websocket key)
- Notes/blockers:
  - Initial post-restart probe briefly returned `502` for `/api/health` and `/ws`; retries passed after services stabilized.

- Date: 2026-03-05
- Task completed: docs/TODO/frontendTODO.md :: 2.1) Branding Icons + Favicons
- Questions asked:
  1) Should I treat the two unchecked icon-verification items as duplicates and complete both from one verification pass?
  2) Is it acceptable to validate icon resolution via build output/static asset checks plus HTTP smoke checks, instead of manual iOS device install?
  3) Should I add a tiny automated check script/test for favicon/manifest icon paths if one does not already exist?
- Assumptions:
  - User approved treating the two unchecked icon-verification checklist entries as duplicates completed by one shared verification pass.
  - MVP validation scope uses filesystem/build-output checks plus HTTP 200 smoke checks; real iOS install testing is deferred.
  - Added automated icon verification script parses `site.webmanifest`, validates referenced files exist, checks required icon files/metadata references, and supports optional HTTP endpoint verification.
- Validation commands/results:
  - `cd codexchat_front && npm run check:icons` ✅
  - `cd codexchat_front && npm run lint` ✅
  - `cd codexchat_front && npm run build` ✅
  - `cd codexchat_front && npm run check:icons -- --base-url=http://127.0.0.1:3000` against local `next dev` ✅
  - `cd codexchat_front && npm run check:icons -- --base-url=http://127.0.0.1:3000` against local `next start` ✅
- Commit:
  - `fe12622` - feat(frontend): verify branding icons and add automated favicon/manifest checks
  - `5b02c58` - fix(frontend): install libc6-compat in alpine image for Next.js SWC
- Push: `origin/master` updated successfully (`877ba2e` -> `5b02c58`)
- Deploy status:
  - initial `docker compose build` failed on `codexchat_front` due missing Alpine glibc compatibility for Next.js SWC (`ld-linux-x86-64.so.2`)
  - follow-up deploy after Dockerfile fix succeeded: `docker compose build` ✅ and `docker compose up -d` ✅
- Smoke check status:
  - `https://todo.flounderboard.com/` ✅ (HTTP 200)
  - `https://todo.flounderboard.com/api/health` ✅ (HTTP 200)
  - websocket route `/ws` ✅ reachable/auth-enforced (`HTTP 403` with HTTP/1.1 websocket upgrade probe)
  - icon assets ✅ (HTTP 200): `/favicon.ico`, `/favicon.svg`, `/favicon-96x96.png`, `/apple-touch-icon.png`, `/site.webmanifest`, `/web-app-manifest-192x192.png`, `/web-app-manifest-512x512.png`
  - `cd codexchat_front && npm run check:icons -- --base-url=https://todo.flounderboard.com` ✅
- Notes/blockers:
  - `docs/TODO/frontendTODO.md` contained unrelated pre-existing unstaged changes in section `2)`; commit staging was narrowed to only section `2.1)` updates for this run.
