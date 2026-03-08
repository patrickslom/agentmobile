# Chat

## Goal
Define chat-specific product behavior for the main CodexChat experience.

This document is intended to hold focused chat module notes that would otherwise be scattered across broader planning docs.

## Scope
- Chat landing page behavior
- Conversation view behavior
- Composer expectations
- Streaming and response-state UX
- Future chat-specific enhancements

## Current Direction
- Chat lives under the shared app shell at `/chat`.
- The chat landing experience belongs in the main content area, not inside the sidebar.
- Conversation history and new chat actions should feel fast and stable.
- Streaming assistant output should remain the default interaction model.

## Composer
- Users type and send messages from the chat composer.
- The composer should support existing and planned structured context inputs, including uploads and workspace file references.
- Sending a message should produce immediate visible UI feedback so the user knows the request was accepted.

## Response State
- After a user sends a message, the interface should clearly indicate that the agent is working.
- As soon as the send is accepted, the chat should immediately show a pending assistant message with animated `...` in the timeline.
- This waiting state should appear before substantive assistant content arrives.
- Streaming output should replace or follow that same pending assistant message without feeling like a separate disconnected event.
- Avoid showing a separate generic status message like `This conversation is busy` when the same state can be communicated inline in the chat stream.
- While the agent is responding, users should not be able to send additional messages or attach/upload files for that conversation.
- The locked state should be visible to all users currently viewing that conversation so collaboration stays synchronized.

## Sidebar Sync
- When a conversation title and summary become available, the sidebar should update automatically without requiring a page refresh.
- New chats should transition from their temporary sidebar label to the generated title and summary as soon as that data is saved.
- The conversation list should stay in sync with server-side title/summary updates during active chat use, including refreshing after background title/summary generation completes.
- Avoid requiring the user to reload the page to see metadata changes for the conversation they just created.

## FUTURE
- Consider pushing conversation metadata changes over websocket instead of relying on targeted sidebar refreshes after title/summary generation.
- Evaluate whether the pending assistant placeholder should be persisted or remain a transient UI-only state.
