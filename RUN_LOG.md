# RUN LOG (2026-03-06)

## Scope
- Switch app runtime to use existing host/global Codex by default.
- Avoid installing/bundling a second Codex inside backend image.
- Keep onboarding behavior: detect global first, then PATH install, prompt install only if no install exists.

## Commands Run

### Host Codex discovery
```bash
which codex && type -a codex
codex --version
npm root -g && node -v
readlink -f /usr/bin/codex
codex login status
```
Key results:
- `codex` found at `/usr/bin/codex` (also `/bin/codex`)
- Resolved script path: `/usr/lib/node_modules/@openai/codex/bin/codex.js`
- Version: `codex-cli 0.111.0`
- Global modules root: `/usr/lib/node_modules`
- Login: `Logged in using ChatGPT`

Pass/fail note:
- PASS: host-global Codex install exists and is authenticated.

### Build/config validation
```bash
bash -n scripts/setup.sh
docker compose config
docker compose build backend worker
docker compose up -d backend worker
```
Key results:
- `setup.sh` syntax check passed.
- Compose renders host Codex runtime bind mounts for backend/worker:
  - host node binary -> container node path
  - host global node_modules -> container node_modules
  - host `~/.codex` -> container `~/.codex`
- Backend/worker rebuilt and started successfully.

Pass/fail note:
- PASS: compose/runtime wiring updated and services recreated.

### In-container Codex runtime checks (protocol-level confidence)
```bash
docker compose exec -T backend sh -lc 'which codex && readlink -f /usr/local/bin/codex && codex --version && codex login status'
docker compose exec -T worker sh -lc 'which codex && codex --version && codex login status'
docker compose exec -T backend sh -lc 'which node && node -v && echo NODE_PATH=$NODE_PATH'
docker compose exec -T backend python - <<PY
import urllib.request
print(urllib.request.urlopen("http://127.0.0.1:8000/api/health").status)
print(urllib.request.urlopen("http://127.0.0.1:8000/api/health").read().decode())
PY
curl -sS --http1.1 -D /tmp/ws_headers_new.txt -o /tmp/ws_body_new.txt \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  https://todo.flounderboard.com/ws
```
Key results:
- Back container:
  - `codex` path resolves to `/usr/local/lib/node_modules/@openai/codex/bin/codex.js`
  - `codex-cli 0.111.0`
  - `Logged in using ChatGPT`
- Worker container:
  - `codex-cli 0.111.0`
  - `Logged in using ChatGPT`
- Node runtime in container: `v22.22.0`
- Backend local health: `200 {"status":"ok"}`
- Websocket unauthenticated upgrade probe: `HTTP/1.1 403 Forbidden` (expected auth enforcement)

Pass/fail note:
- PASS: backend/worker are now using host-global Codex runtime + auth.
- PASS: API health and websocket auth-gate behavior verified.

### Browser-based verification (UX behavior)
```bash
cd /tmp/pwverify && node browser_chat_only.cjs
```
Key results:
```json
{
  "login_to_chat": true,
  "composer_visible": true,
  "lockout_banner_seen": false
}
```

Pass/fail note:
- PASS: browser login-to-chat flow and composer rendering verified after runtime changes.

## Checklist Impact
- No TODO checkbox changes were made in this run.
- Reason: this run focused on Codex runtime source policy (global-first + container reuse), not full re-validation of all backendTODO section 13 behavior.
- Reference TODO file: [docs/TODO/backendTODO.md](/root/agentmobile/docs/TODO/backendTODO.md)

