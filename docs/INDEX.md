# Index

- [INDEX.md](/root/codexchat/docs/INDEX.md)
  Master index of repository documentation files with short summaries and direct links.

- [README.md](/root/codexchat/README.md)
  Public project overview and setup guide for users (requirements, install flow, safety warnings, architecture, defaults).

- [codexchatmvp.md](/root/codexchat/docs/codexchatmvp.md)
  Detailed product and architecture specification for the MVP and MVP+ roadmap.

- [frontendTODO.md](/root/codexchat/docs/TODO/frontendTODO.md)
  Ordered, granular frontend implementation checklist (UI, mobile behavior, streaming, files, settings, admin).

- [backendTODO.md](/root/codexchat/docs/TODO/backendTODO.md)
  Ordered, granular backend checklist (FastAPI API, websocket streaming, Codex bridge, auth, locks, worker, heartbeats).

- [dbTODO.md](/root/codexchat/docs/TODO/dbTODO.md)
  Ordered database checklist (Postgres schema, Alembic migrations, soft-delete archive model, indexes, integrity, maintenance).

- [dbMigrations.md](/root/codexchat/docs/dbMigrations.md)
  Database migration workflow, baseline revision details, and Alembic versioning conventions.

- [builderLOOP.md](/root/codexchat/docs/builderLOOP.md)
  Agent execution loop for completing one task at a time: ask questions, build, validate, commit/push, deploy, smoke-check, stop.

- [RULES.md](/root/codexchat/docs/RULES.md)
  Repository operating rules for agents: documentation sync, build loop behavior, safety constraints, architecture conventions, and communication standards.

- [initialPROMPT.md](/root/codexchat/docs/initialPROMPT.md)
  Reusable kickoff prompt to start one agent run on exactly one next task with required questions, validation, push, deploy, smoke checks, and stop behavior.

- [gnomeCREDIT.md](/root/codexchat/docs/gnomeCREDIT.md)
  Credit/reference note for the garden gnome ASCII used in the setup experience.

- [BROWSERUSE.md](/root/codexchat/docs/BROWSERUSE.md)
  Browser automation guide for Chromium + Playwright setup, runtime dependencies, usage patterns, and troubleshooting.

- [CHANGELOG.md](/root/codexchat/docs/CHANGELOG.md)
  Change log instructions and newest-first record of implemented repository changes.

- [CHAT.md](/root/codexchat/docs/CHAT.md)
  Focused chat module planning document covering chat behavior, composer expectations, response-state UX, and future chat ideas.

- [BOOKMARKD.md](/root/codexchat/docs/BOOKMARKD.md)
  Feature plan for saving assistant messages as user-scoped bookmarks with list and retrieval flows.

- [CONTEXT_ORCHESTRATION.md](/root/codexchat/docs/CONTEXT_ORCHESTRATION.md)
  Plan for backend-driven project selection, memory loading, and auditable memory write orchestration.

- [FILEREF.md](/root/codexchat/docs/FILEREF.md)
  Planning document for `@` workspace file references in the composer, send payload, and agent runtime.

- [HEARTBEATPLAN.md](/root/codexchat/docs/HEARTBEATPLAN.md)
  Guided heartbeat wizard plan covering scheduling, markdown-backed instructions, safety controls, and testing.

- [INTEGRATIONS.md](/root/codexchat/docs/INTEGRATIONS.md)
  Plan for optional external storage and database integrations while preserving local VPS defaults.

- [MEMORYPLAN.md](/root/codexchat/docs/MEMORYPLAN.md)
  Markdown-first memory system plan for global and project-specific memory files and conventions.

- [models.md](/root/codexchat/docs/models.md)
  Findings on current `codexchat` model-selection support, Codex runtime capabilities, and likely implementation options.

- [MODULES.md](/root/codexchat/docs/MODULES.md)
  Route-first app module layout direction for chat, bookmarks, projects, heartbeats, and settings.

- [MULTIUSER.md](/root/codexchat/docs/MULTIUSER.md)
  Multi-user conversation UI plan and implementation notes for participant identity and message presentation.

- [ONBOARDING.md](/root/codexchat/docs/ONBOARDING.md)
  VPS onboarding story covering one-line install, setup flow, access choices, and first-chat path.

- [PROJECTPLAN.md](/root/codexchat/docs/PROJECTPLAN.md)
  Project-aware clarification flow plan for binding conversations to the correct project context.

- [TITLESUMMARY.md](/root/codexchat/docs/TITLESUMMARY.md)
  Plan for generating conversation titles and short summaries from early chat exchanges.

- [initialPROMPT-BACK.md](/root/codexchat/docs/initialPROMPT-BACK.md)
  Backend-specific execution prompt template for one-task builder-loop runs on the production host.

- [initialPROMPT-DB.md](/root/codexchat/docs/initialPROMPT-DB.md)
  Database-specific execution prompt template for one-task builder-loop runs on the production host.

- [initialPROMPT-FRONT.md](/root/codexchat/docs/initialPROMPT-FRONT.md)
  Frontend-specific execution prompt template for one-task builder-loop runs on the production host.
