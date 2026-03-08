# File Reference Plan

## Goal
Add a Codex-style `@` file reference flow to CodexChat so a user can type `@`, search files in the workspace, select one or more matches, and send the message with those file references available to the agent as context.

This is a planning doc only. Do not implement from this document until the UX and backend contract are aligned.

## Recommendation
Use `@` references as a first-class message feature, not as plain text parsing only and not as uploaded duplicates.

Recommended model:
- frontend detects `@` mention intent inside the composer
- frontend opens a file picker immediately when `@` is typed
- selected items are stored as structured file references on the draft message
- websocket `send_message` includes those file references as metadata
- backend resolves those references to safe absolute workspace paths
- runtime prompt includes the resolved paths in the same way current file attachments are injected today

This is the best fit for the current app because the backend already knows how to give Codex file paths through the prompt. The missing piece is a new source of file paths: workspace file references instead of uploaded files.

## Aligned Decisions
These decisions are now considered the planned direction for v1:
- selected refs appear in the composer as filename-only `@name.ext` text
- search scope is the configured workspace root
- websocket `send_message` carries structured `file_refs`
- backend stores those refs in `message.metadata_json`
- agent file access is required, not optional, when valid `file_refs` are sent
- picker opens from workspace root every time
- selecting a file closes the picker immediately
- v1 is single-select only
- folders are navigable only and cannot be attached
- composer display uses filename-only text while full path is stored in structured metadata
- sent workspace refs should be visually distinct from uploads, using a light green treatment
- canceling the picker leaves the typed `@` symbol in place
- search/browse hides nothing by default
- if a selected ref no longer resolves at send time, block the send
- picker default view is current directory contents only, not recent files

## Hard Requirement
When a user sends one or more valid `@` file references, the backend must make those files available to the agent for that turn in a way that allows the agent to actually read them from disk.

This is not a soft prompt hint. It is a feature contract.

Minimum contract:
- selected `file_refs` must be resolved to safe absolute workspace paths
- those resolved paths must be included in the runtime turn input
- the runtime must be able to open/read those files during the turn
- the UI should represent that those files were attached as context, not merely mentioned in text

Non-goal:
- do not treat `@path` as decorative syntax with no guaranteed file access

## Why This Shape
### Better than plain text only
If the user types `@foo` and we only leave text in the prompt, resolution becomes fuzzy and unreliable. Structured refs let the UI show exactly what was selected and let the backend validate it deterministically.

### Better than reusing uploads literally
Uploads are for external files entering the app. Workspace refs are different:
- no binary copy is needed
- no duplicate storage is needed
- the selected path should stay tied to the actual project workspace

### Why modal/sheet is better here
For this app, a picker modal or mobile sheet is a better fit than a tiny inline dropdown:
- mobile screens do not have much room for long path results
- tapping folders is easier than typing exact path fragments on a phone
- one picker can support both browsing and search
- desktop can still use the same component as a centered modal

## Product Behavior
### User flow
1. User types in the composer.
2. When the user types `@` in a mention-eligible position, open the file picker immediately.
3. The picker supports both directory navigation and workspace-root search.
4. On desktop, keyboard navigation should work with `Arrow` keys, `Enter`, and `Esc`.
5. On mobile, the picker should behave as a bottom sheet or full-screen chooser.
6. After selection, the composer inserts literal `@path` text.
7. On send, the message carries:
   - normal text content
   - selected file references as structured metadata
8. Backend resolves those refs to real workspace paths and includes them in the turn context.
9. The sent message shows the selected file refs similarly to attachments so the user can confirm what context was included.

### Match behavior
Suggested search targets:
- file name
- relative path
- optionally recent/opened files later, but not in v1

Suggested ranking:
1. exact filename prefix
2. filename contains query
3. path contains query
4. shorter relative paths slightly favored

### Display
Never show absolute paths in UI.

Composer token behavior for v1:
- insert/display filename-only text such as `@chat-workspace.tsx`
- keep the full workspace-relative path in structured metadata behind the scenes

Sent message behavior:
- show a visually distinct workspace-ref chip/card in a light shade of green
- include enough detail in the sent-message UI to disambiguate the actual selected path
- do not visually present workspace refs as normal uploads

Important tradeoff:
- filename-only composer display is simpler, but duplicate filenames can be ambiguous to the user
- the structured selected ref remains authoritative even if the visible text is shortened

### Picker behavior
Recommended default:
- typing `@` opens the picker immediately
- picker includes a search field at the top
- picker allows folder navigation and file selection
- picker starts at the workspace root every time
- picker default view shows current directory contents only
- picker inserts filename-only `@name.ext` text into the composer while preserving the real relative path in structured state
- selecting a file closes the picker immediately

## Recommended Scope For V1
### Include
- single workspace root search
- directory navigation inside the picker
- files only, not directories
- modal/sheet picker opened immediately by `@`
- single-file selection only for v1
- structured refs attached to a sent message
- backend validation that selected paths stay inside allowed workspace

### Exclude
- fuzzy symbol search inside files
- grep/content search
- cross-workspace search
- automatic file content embedding in the browser
- permissions broader than current runtime workspace

## Architecture
### Frontend
Add a small mention state machine to the composer in [`/root/codexchat/codexchat_front/components/chat/chat-workspace.tsx`](/root/codexchat/codexchat_front/components/chat/chat-workspace.tsx).

Likely draft state:
- `fileRefQuery`
- `fileRefPickerOpen`
- `fileRefResults`
- `fileRefCurrentDirectory`
- `fileRefDirectoryItems`
- `selectedFileRefs`
- `activeFileRefIndex`

Suggested draft shape:

```ts
type ComposerFileRef = {
  id: string; // stable client id
  relativePath: string;
  kind: "workspace";
};
```

Important UI rule:
- selected file refs should not depend on reparsing the raw textarea every render

Treat them like attachments/chips owned by composer state. The visible `@path` text can remain in the textarea for familiarity, but the source of truth should be structured state.

Recommended UI shape:
- desktop: centered modal
- mobile: bottom sheet or full-screen picker
- search and browse live in the same picker
- picker opens at workspace root every time
- selecting a file closes the picker immediately

### Backend API
Add lightweight workspace browse/search endpoints, likely under the chat or files domain.

Candidate search endpoint:
- `GET /api/workspace/files/search?q=chat-workspace&limit=20`

Candidate browse endpoint:
- `GET /api/workspace/files/browse?path=codexchat/codexchat_front/components`

Response shape:

```json
{
  "items": [
    {
      "relative_path": "codexchat_front/components/chat/chat-workspace.tsx",
      "display_name": "chat-workspace.tsx"
    }
  ]
}
```

Search implementation should:
- search under the configured Codex workspace root
- return only normalized relative paths
- never expose paths outside the configured root

Visibility rule for v1:
- hide nothing by default
- hidden files, generated directories, and dependency folders are all searchable/browsable unless later restricted

Browse implementation should:
- list only children under the requested relative path
- return normalized relative paths only
- reject traversal and invalid roots
- support file/folder separation in the response

### WebSocket send contract
Current `send_message` already supports `file_ids`. Extend it with a second field for workspace refs.

Candidate shape:

```json
{
  "type": "send_message",
  "conversation_id": "...",
  "content": "Check @codexchat_front/components/chat/chat-workspace.tsx",
  "file_ids": [],
  "file_refs": [
    {
      "kind": "workspace",
      "relative_path": "codexchat_front/components/chat/chat-workspace.tsx"
    }
  ]
}
```

### Backend turn handling
In [`/root/codexchat/codexchat_back/app/domains/chat/websocket.py`](/root/codexchat/codexchat_back/app/domains/chat/websocket.py):
- validate each `relative_path`
- resolve to an absolute path under configured workspace root
- reject traversal or missing files
- store normalized refs in `message.metadata_json`
- include refs in the emitted `message_created` event
- append resolved paths to the runtime prompt alongside current uploaded-file paths
- require those resolved paths to be present in the runtime turn input before the turn starts

Suggested prompt behavior:
- keep one combined “available file paths” section
- do not inline file contents in the prompt
- let Codex read the files from disk as needed

Required runtime behavior:
- if valid `file_refs` were selected, the turn must run with those file paths available for reading
- do not silently downgrade to “the user mentioned these files” semantics
- if resolution fails, return a clear error instead of pretending the refs were attached

### Persistence
Store file refs in `message.metadata_json` first.

That is the lowest-friction path because the app already uses message metadata and does not yet have a dedicated table for workspace refs.

Example metadata:

```json
{
  "file_refs": [
    {
      "kind": "workspace",
      "relative_path": "codexchat_front/components/chat/chat-workspace.tsx"
    }
  ]
}
```

If this grows later, a normalized `message_file_refs` table can be introduced. It is probably unnecessary for v1.

## Search Strategy
Use a backend index/search service, not browser-side filesystem assumptions.

Possible v1 implementation options:

### Option A: on-demand `rg --files` plus filter
Pros:
- simple
- accurate against live workspace
- good enough for moderate repos

Cons:
- may be slower on very large trees if called on every keystroke

### Option B: cached file list with periodic refresh
Pros:
- fast interactive picker
- predictable latency

Cons:
- cache invalidation work
- more moving parts

Recommendation:
- start with Option A plus frontend debounce
- move to cached index only if the repo size justifies it

Browsing can remain direct filesystem listing in v1. Search and browse do not need the same implementation strategy.

## Security Constraints
This feature must be stricter than the UI makes it appear.

Required checks:
- all refs must resolve under configured Codex workspace root
- reject `..`, symlink escape, and non-existent targets
- files only for v1
- user never sends raw absolute host paths
- search endpoint should return relative paths only

## UX Edge Cases
### Ambiguous `@`
Do not trigger picker for every `@` blindly.

Examples that may need suppression:
- email addresses
- code blocks
- already completed token chips

Practical rule for v1:
- trigger when `@` starts a token boundary in plain composer text
- when triggered, open the picker immediately

### Mobile
Mobile is a first-class case here:
- use a bottom sheet or full-screen picker
- support folder navigation with large tap targets
- keep search available at the top of the picker
- selected workspace refs should render distinctly from uploads using a light green visual treatment

### Missing file at send time
If a file was selected and then deleted or renamed before send:
- fail that send with a clear error
- do not silently drop the ref
- do not silently substitute a different file
- do not allow the send to continue until the broken ref is removed or replaced

### Too many refs
Set a cap in v1.

Suggested cap:
- 10 selected file refs per message

## Remaining Open Questions
1. In the sent message UI, should a workspace ref show both filename and relative path by default, or filename first with expandable path detail?
2. If two files share the same filename, should the picker force extra path context before insertion so the composer text is less ambiguous?
3. Should replacement UX for a broken ref reopen the picker automatically, or just show an error and let the user trigger it again?

## Recommended Decision
If we want the closest behavior to Codex CLI with the least architectural risk:
- add backend workspace file search
- add backend workspace browse support
- add structured `file_refs` on `send_message`
- resolve refs to safe workspace paths in the websocket turn handler
- store refs in `message.metadata_json`
- require those resolved paths to be available to the runtime so the agent can read them
- open a modal/sheet picker immediately when `@` is typed
- show sent refs in the UI like lightweight attachments

That gives us deterministic behavior, low schema churn, and a clear upgrade path later.

## Proposed Next Alignment Step
Before implementation, align on these three decisions:
1. Exact sent-message chip layout for workspace refs
2. Duplicate-filename handling rules
3. Broken-ref recovery flow after a blocked send
