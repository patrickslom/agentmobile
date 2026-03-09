# Frontend TODO

## 0) Project Bootstrap
- [x] Create Next.js app with TypeScript and Tailwind in `frontend`. (completed 2026-03-05)
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
- [x] Add brand logo beside `AGENTMOBILE` on the landing page header and scale for visibility. (completed 2026-03-05)

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
- [x] Add search input in sidebar. (completed 2026-03-06)
- [x] Wire search input to conversation search endpoint. (completed 2026-03-06)
- [x] Show filtered results with loading/empty states. (completed 2026-03-06)
- [x] Preserve selected conversation state during search clear/reset. (completed 2026-03-06)

## 9) Settings Page
- [x] Build settings sections: `Appearance`, `Execution`, `Uploads`, `Heartbeats`, `Safety`. (completed 2026-03-06)
- [x] Load current user settings from backend. (completed 2026-03-06)
- [x] Save settings via patch endpoint. (completed 2026-03-06)
- [x] Add execution mode selector (`regular` / `yolo`) with warning modal. (completed 2026-03-06)
- [x] Add heartbeat defaults UI (disabled by default, cap controls). (completed 2026-03-06)
- [x] Add heartbeat cap control (`10` default, `unlimited` option). (completed 2026-03-06)
- [x] Add upload size limit control (`15 MB` default). (completed 2026-03-06)
- [x] Add shared-workspace non-privacy warning panel. (completed 2026-03-06)

## 10) Admin Settings Page
- [x] Restrict `/settings/admin` visibility to admin users. (completed 2026-03-06)
- [x] Add user table (email, role, status, created date). (completed 2026-03-06)
- [x] Add create-user form (email, temporary password). (completed 2026-03-06)
- [x] Add force-password-reset toggle for new users (default on). (completed 2026-03-06)
- [x] Add disable/enable user actions. (completed 2026-03-06)
- [x] Add reset-password action flow. (completed 2026-03-06; includes explicit missing-endpoint fallback notice for `POST /api/admin/users/:id/reset-password`)
- [x] Add success/error toasts for admin actions. (completed 2026-03-06)

## 11) Heartbeat Jobs UI (MVP+)
- [x] Add heartbeat jobs list screen. (completed 2026-03-06)
- [x] Add create job form: conversation, markdown file path, interval(s), enabled. (completed 2026-03-06)
- [x] Add interval presets: `5/10/15/30/60`. (completed 2026-03-06)
- [x] Add edit job flow. (completed 2026-03-06)
- [x] Add delete job flow. (completed 2026-03-06)
- [x] Add run history view (status + timestamps + errors). (completed 2026-03-06)

## 12) Safety + UX Guardrails
- [x] Show global warning banner about destructive VPS actions. (completed 2026-03-06)
- [x] Show explicit warning when YOLO mode is enabled. (completed 2026-03-06)
- [x] Show notice that shared VPS mode is not private. (completed 2026-03-06)
- [x] Add confirmation dialog before high-risk actions. (completed 2026-03-06)

## 13) Polish + Manual QA Pass
- [ ] Verify mobile layout on narrow screens and modern phones.
- [ ] Verify desktop layout parity with target ChatGPT-like structure.
- [ ] Verify new chat/resume/search flows end-to-end.
- [ ] Verify streaming UX and lock-state UX under contention.
- [ ] Verify attachments upload/download and path visibility in messages.
- [ ] Verify settings persistence and admin user-management flows.
