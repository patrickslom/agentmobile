# Memory Plan (AGENTMOBILE)

## Goal
Create a simple, durable memory system using markdown files that supports:
- global (cross-project) memory
- project-specific memory
- clear agent behavior via `AGENTS.md`

## Design Principles
- Markdown-first and human-readable.
- Fast to update during normal coding sessions.
- Separate "global truths" from "project details".
- Keep audit logs and memory notes distinct.

## Proposed File Layout
```text
/root/agentmobile/AGENTS.md
/root/agentmobile/docs/memory/README.md
/root/agentmobile/docs/memory/GLOBAL.md
/root/agentmobile/docs/memory/DECISIONS.md
/root/agentmobile/docs/memory/OPERATIONS.md
/root/agentmobile/docs/memory/projects/<project-slug>/INDEX.md
/root/agentmobile/docs/memory/projects/<project-slug>/DECISIONS.md
/root/agentmobile/docs/memory/projects/<project-slug>/TASKS.md
/root/agentmobile/docs/memory/projects/<project-slug>/HANDOFF.md
/root/agentmobile/docs/memory/templates/ADR_TEMPLATE.md
/root/agentmobile/docs/memory/templates/HANDOFF_TEMPLATE.md
```

## What Goes Where
- `GLOBAL.md`
  - stable cross-project facts (runtime model, auth model, deployment assumptions)
  - glossary of shared terms
- `DECISIONS.md`
  - repository-wide ADR index (short list with links)
  - major architectural/product decisions
- `OPERATIONS.md`
  - operational runbook notes (safe deploy/rollback/checklist pointers)
  - non-sensitive procedures only
- `projects/<slug>/INDEX.md`
  - project purpose, current status, key paths, owners, latest update
- `projects/<slug>/DECISIONS.md`
  - project-scoped ADRs and tradeoffs
- `projects/<slug>/TASKS.md`
  - prioritized next work and blockers
- `projects/<slug>/HANDOFF.md`
  - "what changed today", "what is next", "known risks"

## Relationship To Existing Files
- `RUN_LOG.md` remains command-level execution/audit history.
- `LOCK.md` remains runtime lock state, not long-term memory.
- Memory files capture durable context and decision rationale.

## AGENTS.md Role (Project-Local)
Create a repo-local `AGENTS.md` that defines:
- memory file locations and naming conventions
- required memory updates after major changes
- read order before starting work:
  1. relevant `projects/<slug>/INDEX.md`
  2. project `HANDOFF.md`
  3. global `DECISIONS.md` / `GLOBAL.md`
- write rules:
  - append, do not rewrite history silently
  - timestamp meaningful updates
  - link decisions to changed code paths when possible

## ADR Usage
ADR = Architecture Decision Record.

Use ADRs for decisions that are hard to reverse, such as:
- data model contracts (`projects`, conversation ownership)
- runtime execution model (`container` vs `host`)
- heartbeat safety defaults and constraints

Each ADR should include:
- Context
- Decision
- Alternatives considered
- Consequences

## Suggested Metadata (Optional Frontmatter)
```md
---
last_updated: 2026-03-07
owner: backend
status: active
---
```

## Integration With Project-Aware Plan
The existing project plan includes `projects.index_md_path`.
Recommended mapping:
- `index_md_path` -> `docs/memory/projects/<project-slug>/INDEX.md`

This keeps app-level project selection aligned with markdown memory.

## Operating Rhythm
- On major change: update project `HANDOFF.md` + `TASKS.md`.
- On major decision: add ADR entry and reference it from project/global decision index.
- Weekly or milestone review: prune stale tasks and refresh `INDEX.md` summaries.

## Next Implementation Step
Scaffold memory directories/files and add a first-pass `AGENTS.md` policy file in repo root.
