# Initial Prompt

Use this prompt to start an agent run:

```text
You are working in /root/codexchat.

Follow these files strictly:
- docs/RULES.md
- docs/builderLOOP.md
- docs/INDEX.md
- docs/TODO/frontendTODO.md
- docs/TODO/backendTODO.md
- docs/TODO/dbTODO.md

Execution requirements for this run:
1) Select exactly one next unchecked task using builderLOOP priority/order.
2) Announce the selected task with file path + exact checklist line.
3) Ask me exactly 3 short questions before implementing.
4) Implement only that task (and minimal required sub-work).
5) Validate your changes.
6) Update the TODO checkbox to complete.
7) Commit with a clear message.
8) Push to origin master.
9) Rebuild/restart containers.
10) Run smoke checks.
11) Report results (files changed, commit hash, deploy status, smoke status).
12) Stop.

Hard constraints:
- Do not start a second task in the same run.
- If blocked, stop and report exact blocker.
- If push/deploy/smoke fails, do not mark task complete.
- Keep docs in sync (README.md + docs/codexchatmvp.md when behavior changes).
- Any new markdown file must be added to docs/INDEX.md.
```

## Optional Add-on (Use When Needed)

```text
Before implementing, provide a 5-bullet micro-plan for this specific task.
```
