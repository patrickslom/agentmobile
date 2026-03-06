You are working in /root/codexchat.

  Follow these files strictly:
  - docs/RULES.md
  - docs/builderLOOP.md
  - docs/INDEX.md
  - docs/codexchatmvp.md
  - docs/TODO/frontendTODO.md
  - docs/TODO/backendTODO.md
  - docs/TODO/dbTODO.md

  Execution requirements for this run:
  1) Select the next unchecked `##` section using
  builderLOOP priority/order.
  2) For this run, select from docs/TODO/backendTODO.md.
  3) Complete the entire selected `##` section in one run
  (all unchecked checklist items under that heading).
  4) Announce the selected section with file path + exact
  `##` heading text.
  5) Ask me exactly 3 short questions before implementing.
  6) Implement only that section (and minimal required sub-
  work).
  7) Validate your changes (lint/typecheck/build if
  available).
  8) Update the TODO checklist items in that section to
  complete with date notes.
  9) Commit with a clear message, staging only files you edited for this run unless I explicitly say otherwise.
  10) Push to origin master.
  11) Before rebuild/restart, check `LOCK.md`, acquire the
  lock per docs/builderLOOP.md, then rebuild/restart
  containers; release/reset `LOCK.md` after deploy.
  12) Run smoke checks (web reachable on active dev host).
  13) Report results: files changed, commit hash, deploy
  status, smoke status.
  14) Stop.

  Important context for this VPS:
  - Current active dev host is todo.flounderboard.com
  routed to codexchat_front.
  - Existing Traefik network is n8n_default; do not create
  a new network.
  - This domain routing is temporary and documented in
  docs/codexchatmvp.md.
  - README.md should not be changed for VPS-specific
  temporary domain notes.

  Hard constraints:
  - Do not start a second `##` section in the same run.
  - If blocked, stop and report exact blocker.
  - If unrelated files are already modified, do not ask what to do; leave them unstaged and commit only files you edited in this run.
  - If push/deploy/smoke fails, do not mark task complete.
  - Never run container rebuild/restart without first
  checking `LOCK.md` and following lock coordination from
  docs/builderLOOP.md.
  - Keep changes tightly scoped to the selected section.
