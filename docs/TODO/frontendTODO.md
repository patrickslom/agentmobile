# Frontend TODO

## 0) Project Bootstrap
- [x] Create Next.js app with TypeScript and Tailwind in `codexchat_front`. (completed 2026-03-05)
- [x] Set up base folder structure: `app/`, `components/`, `lib/`, `hooks/`, `types/`. (completed 2026-03-05)
- [x] Add global style tokens for black/white theme and dark mode variables. (completed 2026-03-05)
- [ ] Add app shell layout with responsive viewport and safe-area handling.
- [ ] Add API base URL and WebSocket URL environment wiring.

## 1) Routing and App Shell
- [ ] Create route: `/login`.
- [ ] Create route: `/chat` (main app).
- [ ] Create route: `/settings`.
- [ ] Create route: `/settings/admin`.
- [ ] Add auth guard redirect logic (`/chat` and `/settings*` require session).
- [ ] Add logout action in shell.

## 2) Theme and Visual System
- [ ] Implement ChatGPT-like structure and spacing system (desktop + mobile).
- [ ] Implement default light mode.
- [ ] Implement dark mode toggle persisted to local storage.
- [ ] Ensure black/white-first palette in both themes.
- [ ] Add typography and code block styling.

## 3) Login UX
- [ ] Build login form (email/password).
- [ ] Connect login form to backend session endpoint.
- [ ] Show generic auth errors.
- [ ] Handle lockout response states with clear user message.
- [ ] Redirect successful login to `/chat`.

## 4) Chat Layout (Desktop + Mobile)
- [ ] Build desktop split layout: left sidebar + main pane.
- [ ] Build mobile top bar with hamburger button.
- [ ] Implement full-screen sidebar drawer on mobile.
- [ ] Add `New chat` button in sidebar.
- [ ] Add conversation list with title + updated timestamp.
- [ ] Add conversation click-to-resume behavior.
- [ ] Add loading/empty/error states for conversation list.

## 5) Message Timeline + Streaming
- [ ] Build message list rendering for `user|assistant|system`.
- [ ] Add markdown rendering with code blocks and inline code.
- [ ] Add copy button for code blocks.
- [ ] Add WebSocket connection manager for `/ws`.
- [ ] Handle `assistant_delta` streaming updates.
- [ ] Handle `assistant_done` finalize event.
- [ ] Handle websocket reconnect + basic retry UX.
- [ ] Show per-conversation busy/lock state when active run exists.

## 6) Composer + Send Flow
- [ ] Build multiline composer (`Enter` send, `Shift+Enter` newline).
- [ ] Disable send while thread is locked/busy.
- [ ] Send `send_message` payload with `conversationId` + content.
- [ ] Show optimistic user message before streamed response.
- [ ] Add clear error handling for failed sends.

## 7) File Attachments UX
- [ ] Add attachment picker button in composer (desktop + mobile).
- [ ] Show pre-send selected file chips with remove action.
- [ ] Upload selected files to backend conversation files endpoint.
- [ ] Include returned file path/reference in message send payload.
- [ ] Render attached file references/paths in message timeline.
- [ ] Render downloadable file links for assistant-returned files.
- [ ] Enforce frontend file size validation (default 15 MB from settings).

## 8) Conversation Search (MVP+ UI)
- [ ] Add search input in sidebar.
- [ ] Wire search input to conversation search endpoint.
- [ ] Show filtered results with loading/empty states.
- [ ] Preserve selected conversation state during search clear/reset.

## 9) Settings Page
- [ ] Build settings sections: `Appearance`, `Execution`, `Uploads`, `Heartbeats`, `Safety`.
- [ ] Load current user settings from backend.
- [ ] Save settings via patch endpoint.
- [ ] Add execution mode selector (`regular` / `yolo`) with warning modal.
- [ ] Add heartbeat defaults UI (disabled by default, cap controls).
- [ ] Add heartbeat cap control (`10` default, `unlimited` option).
- [ ] Add upload size limit control (`15 MB` default).
- [ ] Add shared-workspace non-privacy warning panel.

## 10) Admin Settings Page
- [ ] Restrict `/settings/admin` visibility to admin users.
- [ ] Add user table (email, role, status, created date).
- [ ] Add create-user form (email, temporary password).
- [ ] Add force-password-reset toggle for new users (default on).
- [ ] Add disable/enable user actions.
- [ ] Add reset-password action flow.
- [ ] Add success/error toasts for admin actions.

## 11) Heartbeat Jobs UI (MVP+)
- [ ] Add heartbeat jobs list screen.
- [ ] Add create job form: conversation, markdown file path, interval(s), enabled.
- [ ] Add interval presets: `5/10/15/30/60`.
- [ ] Add edit job flow.
- [ ] Add delete job flow.
- [ ] Add run history view (status + timestamps + errors).

## 12) Safety + UX Guardrails
- [ ] Show global warning banner about destructive VPS actions.
- [ ] Show explicit warning when YOLO mode is enabled.
- [ ] Show notice that shared VPS mode is not private.
- [ ] Add confirmation dialog before high-risk actions.

## 13) Polish + Manual QA Pass
- [ ] Verify mobile layout on narrow screens and modern phones.
- [ ] Verify desktop layout parity with target ChatGPT-like structure.
- [ ] Verify new chat/resume/search flows end-to-end.
- [ ] Verify streaming UX and lock-state UX under contention.
- [ ] Verify attachments upload/download and path visibility in messages.
- [ ] Verify settings persistence and admin user-management flows.
