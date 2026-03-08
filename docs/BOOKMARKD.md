# Bookmarkd Feature Plan

## Goal
Let users save helpful assistant responses for quick retrieval later.

## Core User Story
- User reads a response.
- User clicks "Bookmark".
- Response is saved to personal bookmarks.
- User can revisit bookmarks from a dedicated view.

## MVP Behavior
- Bookmark/unbookmark any assistant message.
- Bookmarks are user-scoped.
- Show bookmark status on message cards.
- Provide bookmarks list with:
  - message preview
  - conversation link
  - created timestamp

## Proposed Data Model
### `message_bookmarks`
- `id` (uuid, pk)
- `user_id` (uuid, fk -> users.id)
- `message_id` (uuid, fk -> messages.id)
- `conversation_id` (uuid, fk -> conversations.id)
- `note` (text, nullable)
- `created_at`

Constraints:
- unique (`user_id`, `message_id`) to prevent duplicates.

## API Surface (Draft)
- `POST /api/bookmarks` create bookmark
- `DELETE /api/bookmarks/:message_id` remove bookmark
- `GET /api/bookmarks` list current user bookmarks

## UI Notes
- Add bookmark icon on assistant messages.
- Add "Bookmarked" filter/page in sidebar or settings.
- Clicking a bookmark opens the source conversation and scrolls to message.

## Safety and Ownership
- Enforce user ownership for both source message and bookmark record.
- Do not allow cross-user bookmark access in shared deployments.

## Future Extensions
- Bookmark folders/tags.
- Search within bookmarked responses.
- "Add to project memory" action from bookmark detail.

## FUTURE
- Add two bookmark sections:
- `Mine` for personal bookmarks visible only to the current user.
- `Shared` for bookmarks intentionally shared across users in the same deployment.
