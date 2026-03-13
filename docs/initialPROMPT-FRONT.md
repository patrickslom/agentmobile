You are working in /root/agentmobile.

  Follow these files strictly:
  - docs/RULES.md
  - docs/INDEX.md
  - docs/agentmobilemvp.md
  - docs/TODO/frontendTODO.md
  - docs/TODO/backendTODO.md
  - docs/TODO/dbTODO.md

  Execution requirements for this run:
  1) Confirm the requested task scope before implementation.
  2) Implement only the requested work and minimal required sub-
  work.
  3) Validate your changes (lint/typecheck/build if
  available).
  4) Update any relevant TODO or status docs with completion notes.
  5) Commit with a clear message, staging only files you edited for this run unless I explicitly say otherwise.
  6) Push to origin master.
  7) Before rebuild/restart, check `LOCK.md`, then rebuild/restart
  containers; release/reset `LOCK.md` after deploy.
  8) Run smoke checks (web reachable on active dev host).
  9) Report results: files changed, commit hash, deploy
  status, smoke status.
  10) Stop.

  Important context for this VPS:
  - Current active dev host is todo.flounderboard.com
  routed to frontend.
  - Existing Traefik network is n8n_default; do not create
  a new network.
  - This domain routing is temporary and documented in
  docs/agentmobilemvp.md.
  - README.md should not be changed for VPS-specific
  temporary domain notes.

  Hard constraints:
  - If blocked, stop and report exact blocker.
  - If unrelated files are already modified, do not ask what to do; leave them unstaged and commit only files you edited in this run.
  - If push/deploy/smoke fails, do not mark task complete.
  - Never run container rebuild/restart without first
  checking `LOCK.md`.
  - Keep changes tightly scoped to the requested task.
