# Project Plan: Project-Aware Clarification Flow

## Goal

Add project awareness to AGENTMOBILE so the assistant can reliably determine which project a user means and ask for clarification when ambiguous.

## Scope (Phase 1)

- Introduce a lightweight `projects` domain.
- Associate conversations to a selected project.
- Add backend preflight checks before runtime turns.
- Add structured clarification events to frontend chat UI.
- Persist user selection from numbered options.

## Desired User Experience

When a prompt appears project-specific but no project is selected (or multiple projects are plausible), the assistant asks:

1. Which project are you working on?
2. Numbered options of existing projects.
3. Option to start a new project.

User responds with a number, and the conversation is bound to that project for future turns.

## Proposed Data Model

### `projects` table

- `id` (UUID, PK)
- `user_id` (UUID, FK -> users.id)
- `name` (string)
- `root_path` (string)
- `index_md_path` (string, nullable)
- `is_active` (bool, default true)
- `created_at`, `updated_at`

### `conversations` changes

- Add `user_id` (UUID, FK -> users.id)
- Add `project_id` (UUID, FK -> projects.id, nullable)

## Backend Design

### 1) Ownership boundaries

- Ensure conversation queries filter by authenticated `user_id`.
- Ensure websocket send/resume paths validate ownership.

### 2) Project preflight (before codex turn)

- Evaluate turn context:
  - explicit `conversation.project_id`
  - message mentions matching known project names/paths
  - recent project usage signals
- If ambiguous:
  - skip `codex_process_runner.run_turn`
  - emit `assistant_clarify` event with numbered options

### 3) Clarification resolution

- Detect numeric replies when clarification is pending.
- Map number -> project choice.
- Persist selected project on conversation.
- Continue normal turn execution.

### 4) Prompt context injection

- Prepend project context when available:
  - project name
  - root path
  - optional index markdown summary/path

## Frontend Design

### New websocket event type

- `assistant_clarify`
  - `conversation_id`
  - `question`
  - `options` (`id`, `label`)
  - `expected_reply` (`"number"`)

### UI behavior

- Render clarification as assistant message card.
- Show clickable numbered options.
- Sending an option posts the number as user message.

## API Surface (Draft)

- `GET /api/projects`
- `POST /api/projects`
- `PATCH /api/projects/{project_id}`
- `GET /api/projects/{project_id}/index`
- `POST /api/projects/{project_id}/index/rebuild` (optional, later)

## Rollout Plan

1. Add schema + migration for `projects`, `conversations.user_id`, `conversations.project_id`.
2. Backfill existing rows safely (single-tenant fallback strategy).
3. Add project CRUD endpoints.
4. Add conversation ownership filters.
5. Add websocket preflight + clarification state handling.
6. Add frontend clarify event rendering.
7. Add tests (unit + integration) for ambiguity flow.

## Risks

- Existing global conversations become user-scoped; migration must be explicit.
- Ambiguity heuristics may over-trigger without tuning.
- Shared VPS path access remains sensitive even with project selection.

## Open Questions

1. Should project index markdown be user-authored, auto-generated, or both?
2. Do we allow one conversation to switch projects mid-thread?
3. Should project selection be required at conversation creation for strictness?
4. How many projects should be shown in clarify options (e.g., top 5)?

## Out of Scope (Phase 1)

- Full repository introspection and automatic long-form index generation.
- Multi-project turns in a single prompt.
- Advanced ranking models for project matching.
