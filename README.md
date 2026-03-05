# Codex Chat MVP

Self-hosted ChatGPT-style web app for running Codex on your VPS.

## Project Info

- Current project domain: `www.questflow.net`
- GitHub repository: `https://github.com/patrickslom/codexchat`

## Current Landing Page Copy

- Headline: `From fresh VPS to live Codex chat in minutes.`
- Supporting copy: `Run the installer, open your domain, log in, and start streaming Codex responses from desktop or phone.`
- Supporting copy: `No Telegram flow. Just a clean web app for real chat workflows and file-based collaboration.`

## Warning

Use at your own risk.

This project can execute powerful actions through Codex against your VPS workspace. Misconfiguration, unsafe prompts, or high-trust execution modes (for example YOLO/no-sandbox flows) can cause destructive changes, including data loss or wiping important files on your VPS.

You are responsible for:
- running regular backups/snapshots
- using least-privilege users/permissions
- restricting production usage to secure settings (domain + HTTPS, strong auth, lockouts)
- reviewing high-risk automation (heartbeat jobs, file operations, shell-capable tooling)

Privacy notice:
- Shared VPS mode is collaborative by design. Users should assume conversations, files, and workspace data are visible to other users of this deployment.

Deploy once, then use it from desktop or phone:
- start new chats
- resume previous chats
- upload/download files
- optionally run scheduled heartbeat instructions

## What this is

This project is a simplified Open CLA-style experience with a web UI instead of Telegram.

Core principles:
- Codex app-server is private (never publicly exposed)
- HTTPS via your existing Traefik setup
- mobile-friendly + desktop-friendly chat experience
- modular architecture (`web`, `api`, `db`, optional `redis`, optional `worker`)

Default service/container names:
- `codexchat_front` (frontend)
- `codexchat_back` (backend)
- `codexchat_db` (postgres)
- optional: `codexchat_redis`, `codexchat_worker`

## Requirements

- VPS with Docker and Docker Compose
- Existing Traefik instance and external Docker network
- Production: domain pointing to VPS
- Dev/test fallback: direct VPS IP is supported (not recommended for production)
- Ports `80/443` open for Traefik
- `npm` only if Codex CLI is not already installed (setup can auto-install Codex via npm)

## Quick Start

One-liner install:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/patrickslom/codexchat/master/scripts/install.sh)
```

Manual install:

```bash
git clone <YOUR_REPO_URL>
cd <YOUR_REPO_DIR>
./scripts/setup.sh
```

Then open:
- `https://<APP_DOMAIN>`

Log in and start chatting.

Dev/test option:
- If you do not have a domain yet, you can run with VPS IP access temporarily.
- Treat IP-only mode as non-production and migrate to domain+HTTPS for normal use.
- Setup script warns before enabling IP mode.

What `./scripts/setup.sh` does:
- checks Docker availability
- checks Codex CLI is installed (can auto-install via `./scripts/install-codex.sh`)
- checks Codex login status (can launch interactive `codex login`)
- bootstraps `.env` from `.env.example`
- asks for access mode (`traefik` recommended, `ip` dev/test only)
- auto-detects Traefik Docker network
- offers managed Traefik install if missing
- starts containers (if compose file exists)

What `./scripts/install.sh` does:
- clones/updates the repo to `~/codexchat` by default
- then launches `./scripts/setup.sh`

## .env keys (minimum)

- `APP_DOMAIN` - public app domain (example: `chat.example.com`)
- `ACCESS_MODE` - `traefik` (production) or `ip` (dev/test)
- `TRAEFIK_NETWORK` - name of your existing external Traefik Docker network
- `TRAEFIK_ACME_EMAIL` - email used by Let's Encrypt (when installing managed Traefik)
- `DATABASE_URL` - Postgres connection URL
- `SESSION_SECRET` - long random secret for session signing
- `CODEX_AUTH` - Codex auth configuration/token used on VPS
- `WORKSPACE_PATH` - workspace mounted into API/worker
- `UPLOADS_PATH` - persistent file storage path (MVP local volume)

Optional:
- `REDIS_URL` - recommended for lockouts/rate counters
- `ADMIN_EMAIL` / `ADMIN_PASSWORD` - seed first user

Defaults and limits:
- YOLO mode is available to all users (high risk; use carefully)
- Heartbeat jobs are off by default
- Heartbeat job cap is `10` per user by default (user can set unlimited in Settings)
- Upload max file size is `15 MB` by default (user can modify in Settings)

User management defaults:
- First user is admin (created from VPS shell/SSH bootstrap).
- Public self-signup is disabled by default.
- Admin creates additional users from the web interface (`Settings -> Admin`).
- New users should be forced to reset password on first login.

Managed Traefik installer:
- `./scripts/install-traefik.sh` installs a minimal Traefik stack (`codexchat_traefik`)
- creates/uses your external Traefik network
- configures Let's Encrypt using `TRAEFIK_ACME_EMAIL`

Managed Codex installer:
- `./scripts/install-codex.sh` installs Codex CLI using npm (`@openai/codex`)
- setup then requires login before continuing

One-liner bootstrap installer:
- `./scripts/install.sh` is the script used by the `curl | bash` installation path
- supports overrides:
  - `CODEXCHAT_DIR` for install location
  - `REPO_URL` for custom fork
  - `BRANCH` for non-master install

## Install Walkthrough

1. Run `./scripts/setup.sh`.
2. If Codex CLI is missing, setup offers to install it automatically.
3. If Codex is not logged in, setup can start `codex login`.
4. Setup asks access mode:
   - `traefik` for production (recommended)
   - `ip` for dev/test (warning shown)
5. If Traefik is missing and mode is `traefik`, setup offers managed Traefik install.
6. Setup generates/updates `.env`, validates network/config, and starts containers.
7. Open the printed URL on desktop or mobile and log in.
8. Admin creates additional users from `Settings -> Admin` and shares temporary credentials.

## User Flow

1. Open app URL on desktop or phone.
2. Log in.
3. Click `New chat` to start a conversation.
4. Optionally attach files; app stores them in the managed files directory.
5. Send message and stream Codex responses (attached file paths are sent with the message and shown in chat).
6. Reopen old conversations from sidebar/drawer.
7. Upload files into chat and download generated/shared files.
8. If someone else is actively running the same conversation, app blocks/queues your send until it is free.

Codex integration model:
- This app uses the existing Codex installation/auth on your VPS.
- The backend launches `codex app-server` privately and streams results to the web UI.
- One active Codex run is allowed per conversation/thread at a time (lock/queue behavior).

## Mobile UX expectations

- ChatGPT-like layout on desktop and mobile.
- Full-screen sidebar drawer on mobile (hamburger menu).
- Composer fixed at bottom with safe-area support.
- New/resume flows work the same across devices.

## Theme

- Visual style mimics ChatGPT closely.
- Black-and-white base style.
- Default theme is light mode.
- Dark mode toggle available in UI/settings.

## Heartbeat Automations (MVP+)

Heartbeat jobs let a user send a markdown instruction file to Codex on a schedule.

Examples:
- every 5 minutes
- every 10 minutes
- every 15 minutes
- every 30 minutes
- every 60 minutes

Each run:
1. reads the latest markdown file content
2. sends it into a mapped conversation
3. stores assistant output in normal chat history

Default policy:
- disabled until user enables/creates jobs
- max `10` heartbeat jobs per user by default
- user can change cap to unlimited in Settings

## Architecture (high level)

- `web`: frontend UI
- `api` (FastAPI): auth, chat APIs, websocket streaming, Codex bridge
- `db` (Postgres): users, messages, conversations, job/file metadata
- `redis` (optional): lockouts and counters
- `worker` (optional): heartbeat/scheduled jobs
- `traefik` (external): TLS and routing

Backend defaults:
- cookie-based auth sessions
- spawn-per-turn Codex lifecycle (new Codex app-server process per message turn)

## Security notes

- Never expose Codex app-server port publicly.
- Keep API/Web behind Traefik HTTPS.
- Prefer domain+TLS in production; IP-only mode is dev/test only.
- YOLO mode is high risk and can cause destructive VPS changes.
- Use strong session secrets and password hashing.
- Keep lockout policy enabled for login attempts.

## Roadmap

- Conversation search
- Heartbeat job UI + scheduler worker
- Multi-workspace support
- Object storage backend (S3-compatible)
- OAuth / passkeys / TOTP

## License

MIT or Apache-2.0 (choose one before public release).
