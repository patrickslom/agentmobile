# Rules

## Documentation Rules
- This project is open source and intended for public use once complete; current work is still in-progress development.
- Any new `.md` file added to this directory must also be added to `INDEX.md` with a short summary.
- If you add a markdown file anywhere under `docs/`, update `docs/INDEX.md` in the same change before the work is considered complete.
- If an existing `.md` file is renamed or removed, `INDEX.md` must be updated in the same change.
- Product behavior changes must update both `README.md` (user-facing) and `docs/codexchatmvp.md` (spec-facing).
- `README.md` must be written as production/public-facing documentation for the completed project and should not be used to track current in-progress development status.
- Current development status must be documented in `docs/` files (not in `README.md`).
- TODO progress updates must only check off tasks that are actually implemented and validated.

## Build Execution Rules
- Follow `docs/builderLOOP.md` for execution order and one-task-per-run behavior.
- Start each run by selecting the next unchecked task from TODO files in priority order.
- Ask the user 3 short questions before implementing each task.
- After each completed task: validate, mark TODO complete, commit only files modified in this run, push to `master`, rebuild containers, smoke check, then stop.
- Commit/push rule: write context-rich commit messages that clearly describe what changed, why, and major files affected. Stage only files you modified for the selected task unless the user explicitly requests a broader commit.
- Any time a change is committed or pushed to `master`, update `docs/CHANGELOG.md` in the same run to record the change.

## Safety and Deployment Rules
- Never mark a task complete if push or deploy fails.
- Never expose Codex app-server publicly.
- Treat IP mode as dev/test only; prefer Traefik + HTTPS for production.
- Preserve warning language about destructive risk and shared non-privacy model.
- Do not print secrets from `.env` or secret values in logs/messages.

## Code and Scope Rules
- Consistency is mandatory across all work (code, docs, infra, scripts, and process updates):
  - Before creating anything new, first check whether an existing setup/pattern already exists and follow it.
  - If no suitable existing setup/pattern exists, explicitly state that before introducing a new pattern.
- When designing or generating new features, always prioritize efficiency. Check for potential resource-heavy operations (large data scans, excessive loops, frequent queries), and propose optimized approaches (indexing, caching, or denormalizing) before finalizing any solution.
- All user-facing pages and reusable UI components must be responsive and verified for desktop, tablet, and phone viewports.
- Keep changes scoped to the selected task; do not bundle unrelated refactors.
- Do not remove existing warnings, limits, or lock behavior without explicit user approval.
- Respect core defaults unless user changes them:
  - YOLO available to all users
  - heartbeat disabled by default
  - heartbeat cap 10 by default (optional unlimited)
  - upload limit 15 MB by default
- Concurrency model must remain: one active run per conversation, reject concurrent sends as `thread busy`.

## Architecture Rules
- Keep frontend/backend/db naming consistent:
  - `codexchat_front`
  - `codexchat_back`
  - `codexchat_db`
- Keep backend routing consistent on one domain:
  - `/` frontend
  - `/api/*` backend
  - `/ws` backend
- Maintain split services from day one:
  - API service (`codexchat_back`)
  - worker service (`codexchat_worker`)

## Database Rules
- Use Postgres + Alembic migrations.
- Use recoverable soft delete (`archived_at`) where defined.
- Preserve global shared data model (no privacy assumptions across users).

## Agent Communication Rules
- Be direct and concise.
- Report blockers immediately with exact missing requirement.
- If assumptions are required, state them explicitly before implementation.
