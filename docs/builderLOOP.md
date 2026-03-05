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
- Commit:
- Push:
- Deploy status:
- Smoke check status:
- Notes/blockers:
