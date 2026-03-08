# Context Orchestration Plan

## Goal
Define how CodexChat should coordinate project selection, memory loading, and memory writing so behavior is reliable, safe, and easy to understand.

## Core Principle
Do not rely on prompt instructions alone.

Use a hybrid model:
- deterministic backend orchestration for routing and state changes
- lightweight system prompt for assistant tone and interaction style

## Why Hybrid
- Prompt-only behavior is inconsistent across turns and models.
- Backend rules provide predictable safety and ownership checks.
- Prompt layer remains useful for user-facing phrasing and clarification style.

## Scope
- Project selection and disambiguation before a turn runs.
- Controlled loading of project/global memory into context.
- Explicit and auditable memory writes.
- Correct handling for chats that are not project-based.

## Conversation Modes
Every conversation should be in one of three modes:
- `project_bound`: tied to a specific project (`conversation.project_id` set)
- `general`: not tied to any project (`conversation.project_id` is null)
- `unknown`: temporary state before intent is clear

Mode routing rules:
1. Classify early turns as project-specific or general.
2. If clearly general, set/keep `general` and do not ask project selection.
3. If clearly project-specific and ambiguous, ask project clarification.
4. If unclear, ask one lightweight clarification question, then set mode.

## Project Selection Flow (Only When Needed)
1. User sends message.
2. Backend preflight checks conversation mode:
   - `general`: skip project selector and continue normal turn.
   - `project_bound`: use existing `conversation.project_id`.
   - `unknown`: run intent classification.
3. If intent appears project-specific, resolve project context:
   - if `conversation.project_id` exists, use it.
   - else attempt match from known projects (name/path/signal).
4. If no clear single project match:
   - emit clarification event with numbered options.
   - include option to create a new project.
5. User responds with number or create-new action.
6. Backend binds conversation to selected project and continues turn.

## Clarification UX Contract
- Prompt user with:
  - "Which project are you working on?"
  - numbered project options
  - "Start a new project" option
- Numeric reply is accepted as canonical resolver.
- Optional UI: clickable option chips that send the number.

## Memory Read Policy
When a project is selected, load memory in this order:
1. Project `INDEX.md`
2. Project `HANDOFF.md`
3. Project `DECISIONS.md` (summary slice)
4. Global `DECISIONS.md` / `GLOBAL.md` (minimal slice)

Rules:
- Use summaries and bounded excerpts, not full file dumps.
- Prefer freshness and relevance.
- Keep context size predictable.

For `general` mode:
- load global memory only (`GLOBAL.md`, global decisions summaries)
- do not load project memory files

## Memory Write Policy
Memory writes must be explicit and scoped.

Write triggers:
- explicit user intent ("remember this", "add to memory")
- explicit UI action (Save to memory)

Write flow:
1. Infer target scope (project or global).
2. Generate proposed memory entry.
3. Show preview: destination file + content snippet.
4. Confirm write (or allow opt-in auto-confirm setting for explicit intent).
5. Append entry and record timestamp/actor.

Default safety:
- no silent memory writes
- no cross-project writes without explicit confirmation
- no secret/token persistence in memory docs

Mode-specific write behavior:
- `project_bound`: default target is project memory
- `general`: default target is global memory
- `unknown`: hold writes until scope is clarified

## Ownership and Isolation
- Memory and project resolution are user-scoped.
- Conversations can only bind to projects owned by the authenticated user.
- Shared VPS deployments must assume tenant visibility risks unless isolated by design.

## System Prompt Responsibilities
System prompt should:
- ask concise clarification questions when backend signals ambiguity
- explain where memory will be saved before confirmation
- avoid claiming memory was saved until backend confirms success

System prompt should not:
- make authoritative routing decisions
- perform persistence without backend confirmation

## Backend Responsibilities
- enforce project ownership checks
- perform ambiguity detection and emit clarify events
- resolve numeric clarification replies
- apply memory write guardrails and persistence
- log memory write/read events for auditability

## Suggested API/Event Directions
- Clarification event: `assistant_clarify`
  - `conversation_id`
  - `question`
  - `options[]`
  - `expected_reply: "number"`
- Memory write action:
  - `POST /api/memory/write` (or project/global specific endpoints)
  - payload includes scope, destination file, preview text, confirmation flag

## Initial Defaults for Open Source Distribution
- Memory writes conservative by default (explicit only).
- Project clarification enabled for ambiguous cases.
- Add visible audit trail ("saved to X at timestamp").
- Provide admin/user setting for stricter or looser memory behavior.

## Related Project Docs
- `README.md`
- `MEMORYPLAN.md`
- `docs/PROJECTPLAN.md`
- `docs/HEARTBEATPLAN.md`

## Next Steps
1. Define exact clarify and memory-write event schemas.
2. Implement backend preflight guard for project selection.
3. Add UI cards for clarification and memory write confirmation.
4. Add tests for ambiguous project prompts and explicit memory writes.
