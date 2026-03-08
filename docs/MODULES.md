# Modules

## Direction

The app should use a route-first module layout instead of collapsible content inside the sidebar.

Preferred model:
- The sidebar is for navigation.
- The main content area is where each module renders its landing page and deeper views.
- The URL reflects the active module.

This replaces the earlier desktop-only module rail idea and the later accordion-in-sidebar idea.

## Shared app shell

The protected app should use one shared shell across the main product areas:
- `/chat`
- `/bookmarks`
- `/projects`
- `/heartbeats`
- `/settings`

Shell behavior:
- The sidebar remains visible across all of these routes.
- The main content area swaps based on the active route.
- Settings should no longer feel like a detached page with no path back to the app.
- Heartbeats should also live in this same shell.

## Responsive layout

Desktop:
- The sidebar stays visible on the left.
- The main content stays visible on the right.

Mobile:
- The sidebar is still part of the page.
- No drawer behavior is used.
- The sidebar appears full width.
- The main content appears below the sidebar.

The goal is functional consistency across desktop and mobile, even if the layout stacks differently on small screens.

## Sidebar navigation

The sidebar should be simple and stable.

Sidebar items:
- `Chat`
- `Bookmarks`
- `Projects`
- `Heartbeats`
- `Settings`

Behavior:
- Each item is a straightforward navigation link or button to its route.
- The active route should be visually highlighted.
- The sidebar should not be responsible for rendering full module content inline.
- Users should be able to move between all main product areas without losing the shared shell.

## Module landing pages

Each module should have its own landing page in the main content area.

`/chat`
- Shows the chat landing experience in the main content area.
- Includes search, recent chat history, and new chat actions in the main content area rather than embedding that experience into the sidebar.
- Deeper chat views can continue from there.

`/bookmarks`
- Placeholder landing page for saved prompts, references, and future pinned items.

`/projects`
- Placeholder landing page for future project workspaces.

`/heartbeats`
- Landing page for heartbeat jobs and related controls.

`/settings`
- Shows the settings UI in the main content area.
- Keeps the same sidebar visible.
- Replaces the current detached settings experience.

## Routing

Primary routes:
- `/chat`
- `/bookmarks`
- `/projects`
- `/heartbeats`
- `/settings`

Routing notes:
- The address bar should always reflect the active module.
- Returning from `Settings` does not need to preserve prior chat state.
- Deeper views should continue to live under the active module rather than being hidden inside the sidebar.

## Current scope

For now:
- `Bookmarks` and `Projects` can remain scaffolded placeholders.
- `Heartbeats` should be included as a first-class module in the shared shell.
- The sidebar should be unified across chat, settings, and heartbeats so the app feels like one product surface.

## Obsolete ideas

These earlier directions should be treated as obsolete:
- desktop-only collapsed module rail
- mobile drawer sidebar
- rendering module content directly inside collapsible sidebar sections
