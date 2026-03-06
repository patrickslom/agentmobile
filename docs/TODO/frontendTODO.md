# Frontend TODO

## 0) Project Bootstrap
- [x] Create Next.js app with TypeScript and Tailwind in `codexchat_front`. (completed 2026-03-05)
- [x] Set up base folder structure: `app/`, `components/`, `lib/`, `hooks/`, `types/`. (completed 2026-03-05)
- [x] Add global style tokens for black/white theme and dark mode variables. (completed 2026-03-05)
- [x] Add app shell layout with responsive viewport and safe-area handling. (completed 2026-03-05)
- [x] Add API base URL and WebSocket URL environment wiring. (completed 2026-03-05)

## 1) Routing and App Shell
- [x] Create route: `/login`. (completed 2026-03-05)
- [x] Create route: `/chat` (main app). (completed 2026-03-05)
- [x] Create route: `/settings`. (completed 2026-03-05)
- [x] Create route: `/settings/admin`. (completed 2026-03-05)
- [x] Add auth guard redirect logic (`/chat` and `/settings*` require session). (completed 2026-03-05)
- [x] Add logout action in shell. (completed 2026-03-05)

## 2) Theme and Visual System
- [x] Implement ChatGPT-like structure and spacing system (desktop + mobile). (completed 2026-03-05; user override accepted despite ws smoke failure)
- [x] Implement default light mode. (completed 2026-03-05; user override accepted despite ws smoke failure)
- [x] Implement dark mode toggle persisted to local storage. (completed 2026-03-05; user override accepted despite ws smoke failure)
- [x] Ensure black/white-first palette in both themes. (completed 2026-03-05; user override accepted despite ws smoke failure)
- [x] Add typography and code block styling. (completed 2026-03-05; user override accepted despite ws smoke failure)
- [x] Add brand logo beside `CodexChat` on the landing page header and scale for visibility. (completed 2026-03-05)

## 2.1) Branding Icons + Favicons
- [x] Flatten favicon/icon assets into `public/`, wire metadata in `app/layout.tsx`, and remove default `app/favicon.ico`. (completed 2026-03-05)
- [x] Verify browser tab icon, iOS home screen icon, and PWA manifest icons resolve in local dev and production build. (completed 2026-03-05; verified via `npm run check:icons`, `npm run check:icons -- --base-url=http://127.0.0.1:3000` on dev/start, and production HTTP smoke 200s)
- [x] Ensure browser tab icon, iOS home screen icon, and PWA manifest icons resolve in local dev and production build. (completed 2026-03-05; duplicate checklist item closed using same verification evidence as above)

## 3) Login UX
- [x] Build login form (email/password). (completed 2026-03-05)
- [x] Connect login form to backend session endpoint. (completed 2026-03-05)
- [x] Show generic auth errors. (completed 2026-03-05)
- [x] Handle lockout response states with clear user message. (completed 2026-03-05)
- [x] Redirect successful login to `/chat`. (completed 2026-03-05)

## 4) Chat Layout (Desktop + Mobile)
- [x] Build desktop split layout: left sidebar + main pane. (completed 2026-03-05)
- [x] Build mobile top bar with hamburger button. (completed 2026-03-05)
- [x] Implement full-screen sidebar drawer on mobile. (completed 2026-03-05)
- [x] Add `New chat` button in sidebar. (completed 2026-03-05)
- [x] Add conversation list with title + updated timestamp. (completed 2026-03-05)
- [x] Add conversation click-to-resume behavior. (completed 2026-03-05)
- [x] Add loading/empty/error states for conversation list. (completed 2026-03-05)

## 5) Message Timeline + Streaming
- [x] Build message list rendering for `user|assistant|system`. (completed 2026-03-05)
- [x] Add markdown rendering with code blocks and inline code. (completed 2026-03-05)
- [x] Add copy button for code blocks. (completed 2026-03-05)
- [x] Add WebSocket connection manager for `/ws`. (completed 2026-03-05)
- [x] Handle `assistant_delta` streaming updates. (completed 2026-03-05)
- [x] Handle `assistant_done` finalize event. (completed 2026-03-05)
- [x] Handle websocket reconnect + basic retry UX. (completed 2026-03-05)
- [x] Show per-conversation busy/lock state when active run exists. (completed 2026-03-05)

## 6) Composer + Send Flow
- [x] Build multiline composer (`Enter` send, `Shift+Enter` newline). (completed 2026-03-06)
- [x] Disable send while thread is locked/busy. (completed 2026-03-06)
- [x] Send `send_message` payload with `conversationId` + content. (completed 2026-03-06)
- [x] Show optimistic user message before streamed response. (completed 2026-03-06)
- [x] Add clear error handling for failed sends. (completed 2026-03-06)

## 7) File Attachments UX
- [x] Add attachment picker button in composer (desktop + mobile). (completed 2026-03-06)
- [x] Show pre-send selected file chips with remove action. (completed 2026-03-06)
- [x] Upload selected files to backend conversation files endpoint. (completed 2026-03-06)
- [x] Include returned file path/reference in message send payload. (completed 2026-03-06)
- [x] Render attached file references/paths in message timeline. (completed 2026-03-06)
- [x] Render downloadable file links for assistant-returned files. (completed 2026-03-06)
- [x] Enforce frontend file size validation (default 15 MB from settings). (completed 2026-03-06)

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
