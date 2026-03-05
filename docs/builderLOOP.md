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
9. Commit changes with a task-specific message.
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
- If repo has unrelated dirty changes, do not revert them; work around them.
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
- pushed to `master`
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
git add -A
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
- Commit: `64fd6c2` - feat(frontend): bootstrap Next.js app and deploy questflow.net via existing Traefik network
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
  - `https://www.questflow.net` ✅ (HTTP 200)
  - `https://questflow.net` ✅ (HTTP 200)
- Notes/blockers:
  - `questflow.com` and `www.questflow.com` currently resolve to external IPs (`13.248.169.48`, `76.223.54.146`), so LE cert validation for `.com` cannot occur on this VPS until DNS is updated.

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
