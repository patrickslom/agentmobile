# Multi-User Conversation UI Plan

## Implementation Status

- Completed on 2026-03-07: all checklist items in this plan are implemented in backend and frontend.

## Goal
In shared conversations, clearly separate participants so users can see who said what.

## Decisions Captured
- Use dedicated user identity metadata:
  - Add explicit profile name field (not derived from email) for message labeling.
  - Add optional profile picture field for author avatars.
- Use **snapshot-at-send** author metadata for messages.
- Legacy messages without identity metadata should show `Former User`.

## Desired Message Layout
- Current user messages:
  - label: `YOU`
  - alignment: right
  - style: user bubble style
- Other human users' messages:
  - label: user's display name (example: `JEFF`)
  - alignment: left
  - style: distinct human-peer bubble style
- Assistant messages:
  - label: `Assistant`
  - alignment: left (or neutral container)
  - width: full-width card (not narrow bubble)

## Why
- Removes ambiguity in shared threads.
- Makes collaborative chats readable at a glance.
- Preserves current assistant readability with full-width responses.

## Data Requirements
Message payloads should include author identity fields for human messages:
- `author_user_id`
- `author_display_name`
- `author_profile_picture_url`
- `is_current_user_author` (optional convenience flag)

Snapshot-at-send rules (preferred):
- `author_display_name` and `author_profile_picture_url` are resolved from the authenticated sender at message creation and persisted with the message event.
- If `author_user_id` matches session user -> show `YOU`.
- Otherwise show normalized `author_display_name`.
- Assistant/system messages keep role-based labels.

Legacy compatibility rules:
- Legacy messages without identity metadata should render as `Former User`.
- If identity metadata exists but name is blank after normalization -> `Former User`.

## Backend Changes (High Level)
- Add dedicated user profile identity fields for snapshot-based rendering:
  - `users.display_name` (required, unique constraints and normalization strategy to be defined).
  - `users.profile_picture_url` (optional, nullable).
- Add `messages.user_id` (nullable for assistant/system, required for user role).
- On user-turn writes, set:
  - `messages.user_id` from authenticated sender.
  - `messages.metadata_json.author_user_id`
  - `messages.metadata_json.author_display_name`
  - `messages.metadata_json.author_profile_picture_url`
- Return author identity fields in conversation and websocket message payloads:
  - `author_user_id`
  - `author_display_name`
  - `author_profile_picture_url`
  - `is_current_user_author` (derived per-request).
- Keep shared visibility model (global shared conversations) unchanged.
- Ensure migration + compatibility for historical rows.

## Frontend Changes (High Level)
- Replace role-only labeling with author-aware labeling for `role=user`.
- Add left/right alignment logic based on `is_current_user_author`.
- Keep assistant card full-width.
- Add avatar rendering from `author_profile_picture_url` for human messages.
- Add fallback label `Former User` when identity is missing.

## Open API/DB Contract Draft
- Message payload (`role=user`) should include:
  - `author_user_id: string`
  - `author_display_name: string` (snapshot at send)
  - `author_profile_picture_url?: string | null`
  - `is_current_user_author?: boolean`
- Assistant/system payloads should leave `author_*` absent or null and keep role-based label behavior.

## Edge Cases
- Deleted/deactivated user:
  - keep message visible
  - show fallback label `Former User`
- Name changes:
  - snapshot-at-send so old messages preserve historical display name.
- Legacy rows without `user_id`:
  - render as `Former User` and left-aligned human bubble style.

## Migration Strategy
- Add `display_name` + `profile_picture_url` to `users`.
- Add `messages.user_id` with safe defaulting/null behavior for system rows.
- Backfill `messages.metadata_json.author_*` for existing user messages using current `users` data where possible.
- Flag unknown historical rows as `Former User`.
- Emit/consume both payload shapes during transition:
  - prefer snapshot fields when present,
  - fallback to legacy behavior only if snapshot fields are missing.

## Acceptance Criteria
- In one shared conversation with two users:
  - user A sees their own messages on right as `YOU`
  - user A sees user B messages on left as `B`'s name
  - user B sees their own messages on right as `YOU`
  - assistant remains full-width
- No regression to streaming behavior or message retry flow.

## Proposed TODO List
- [x] Backend: add `users.display_name` and `users.profile_picture_url` fields (schema + migration).
- [x] Backend: backfill existing users with deterministic `display_name` values (for example local-part from email), set `profile_picture_url` null.
- [x] Backend: add `messages.user_id` (nullable for assistant/system, required for user role) + DB migration.
- [x] Backend: write user identity snapshot fields to `messages.metadata_json` on all user-message inserts.
- [x] Backend: include author payload fields in `GET /api/conversations/:id` response.
- [x] Backend: include author payload fields in websocket events and ensure `assistant_done`/`assistant_delta` continue unchanged.
- [x] Backend: ensure legacy messages return `Former User` labels in payloads when identity is absent.
- [x] Frontend: extend `ChatMessage` type with optional author fields.
- [x] Frontend: update normalizer for API and websocket event payloads to parse `author_*` fields safely.
- [x] Frontend: render user bubbles with avatar + author label:
  - `YOU` when `is_current_user_author`.
  - `Former User` fallback when display name missing.
- [x] Frontend: switch left/right alignment logic from role-only to `is_current_user_author` for human messages.
- [x] Frontend: maintain assistant full-width card behavior and existing streaming/retry flows.
- [x] QA: document validation pass criteria for shared-room message attribution, legacy fallback, and no UI regressions.
