# Index

- [INDEX.md](/root/agentmobile/docs/INDEX.md)
  Master index of repository documentation files with short summaries and direct links.

- [README.md](/root/agentmobile/README.md)
  Public project overview and setup guide for users (requirements, install flow, safety warnings, architecture, defaults).

- [agentmobilemvp.md](/root/agentmobile/docs/agentmobilemvp.md)
  Detailed product and architecture specification for the MVP and MVP+ roadmap.

- [frontendTODO.md](/root/agentmobile/docs/TODO/frontendTODO.md)
  Ordered, granular frontend implementation checklist (UI, mobile behavior, streaming, files, settings, admin).

- [backendTODO.md](/root/agentmobile/docs/TODO/backendTODO.md)
  Ordered, granular backend checklist (FastAPI API, websocket streaming, Codex bridge, auth, locks, worker, heartbeats).

- [dbTODO.md](/root/agentmobile/docs/TODO/dbTODO.md)
  Ordered database checklist (Postgres schema, Alembic migrations, soft-delete archive model, indexes, integrity, maintenance).

- [dbMigrations.md](/root/agentmobile/docs/dbMigrations.md)
  Database migration workflow, baseline revision details, and Alembic versioning conventions.

- [builderLOOP.md](/root/agentmobile/docs/builderLOOP.md)
  Agent execution loop for completing one task at a time: ask questions, build, validate, commit/push, deploy, smoke-check, stop.

- [RULES.md](/root/agentmobile/docs/RULES.md)
  Repository operating rules for agents: documentation sync, build loop behavior, safety constraints, architecture conventions, and communication standards.

- [initialPROMPT.md](/root/agentmobile/docs/initialPROMPT.md)
  Reusable kickoff prompt to start one agent run on exactly one next task with required questions, validation, push, deploy, smoke checks, and stop behavior.

- [gnomeCREDIT.md](/root/agentmobile/docs/gnomeCREDIT.md)
  Credit/reference note for the garden gnome ASCII used in the setup experience.

- [BROWSERUSE.md](/root/agentmobile/docs/BROWSERUSE.md)
  Browser automation guide for Chromium + Playwright setup, runtime dependencies, usage patterns, and troubleshooting.

- [CHANGELOG.md](/root/agentmobile/docs/CHANGELOG.md)
  Change log instructions and newest-first record of implemented repository changes.

- [CHAT.md](/root/agentmobile/docs/CHAT.md)
  Focused chat module planning document covering chat behavior, composer expectations, response-state UX, and future chat ideas.

- [BOOKMARKD.md](/root/agentmobile/docs/BOOKMARKD.md)
  Feature plan for saving assistant messages as user-scoped bookmarks with list and retrieval flows.

- [CONTEXT_ORCHESTRATION.md](/root/agentmobile/docs/CONTEXT_ORCHESTRATION.md)
  Plan for backend-driven project selection, memory loading, and auditable memory write orchestration.

- [FILEREF.md](/root/agentmobile/docs/FILEREF.md)
  Planning document for `@` workspace file references in the composer, send payload, and agent runtime.

- [HEARTBEATPLAN.md](/root/agentmobile/docs/HEARTBEATPLAN.md)
  Guided heartbeat wizard plan covering scheduling, markdown-backed instructions, safety controls, and testing.

- [INTEGRATIONS.md](/root/agentmobile/docs/INTEGRATIONS.md)
  Plan for optional external storage and database integrations while preserving local VPS defaults.

- [MEMORYPLAN.md](/root/agentmobile/docs/MEMORYPLAN.md)
  Markdown-first memory system plan for global and project-specific memory files and conventions.

- [models.md](/root/agentmobile/docs/models.md)
  Findings on current `agentmobile` model-selection support, Codex runtime capabilities, and likely implementation options.

- [MODULES.md](/root/agentmobile/docs/MODULES.md)
  Route-first app module layout direction for chat, bookmarks, projects, heartbeats, and settings.

- [MULTIUSER.md](/root/agentmobile/docs/MULTIUSER.md)
  Multi-user conversation UI plan and implementation notes for participant identity and message presentation.

- [ONBOARDING.md](/root/agentmobile/docs/ONBOARDING.md)
  VPS onboarding story covering one-line install, setup flow, access choices, and first-chat path.

- [PROJECTPLAN.md](/root/agentmobile/docs/PROJECTPLAN.md)
  Project-aware clarification flow plan for binding conversations to the correct project context.

- [TITLESUMMARY.md](/root/agentmobile/docs/TITLESUMMARY.md)
  Plan for generating conversation titles and short summaries from early chat exchanges.

- [initialPROMPT-BACK.md](/root/agentmobile/docs/initialPROMPT-BACK.md)
  Backend-specific execution prompt template for one-task builder-loop runs on the production host.

- [initialPROMPT-DB.md](/root/agentmobile/docs/initialPROMPT-DB.md)
  Database-specific execution prompt template for one-task builder-loop runs on the production host.

- [initialPROMPT-FRONT.md](/root/agentmobile/docs/initialPROMPT-FRONT.md)
  Frontend-specific execution prompt template for one-task builder-loop runs on the production host.
