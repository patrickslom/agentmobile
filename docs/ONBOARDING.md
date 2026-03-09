# Onboarding Story (VPS Install)

## Goal
Give users a clear, low-friction path from fresh VPS to first successful chat.

## One-Line Install
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/patrickslom/agentmobile/master/scripts/install.sh)
```

## User Story: End-to-End
1. User SSHs into VPS.
2. User runs one-line install command.
3. Installer clones/updates repo and launches setup.
4. Setup checks Docker and Docker Compose.
5. Setup checks for existing Codex CLI.
6. If Codex is missing, setup offers guided Codex install.
7. Setup checks Codex login status and offers `codex login` if needed.
8. Setup checks security baseline tools (for example `fail2ban`).
9. If `fail2ban` is not found, setup recommends installing it.
10. Setup asks optional tooling questions (see below).
11. Setup asks access choice:
   - use own domain/subdomain (recommended)
   - use managed domain option (`$5/month`)
   - temporary VPS IP mode (dev/test only)
12. Setup validates config, writes `.env`, starts containers.
13. User opens URL, logs in, creates first chat.

## Optional Tooling Prompts
During setup, optionally ask:
- Install GitHub CLI (`gh`)?
- Install Supabase CLI (`supabase`)?
- Install Google Workspace tooling/CLI?
- Install Cloudflare CLI (`wrangler`)?

Notes:
- These are optional quality-of-life tools.
- Core app should still install if user skips all optional CLIs.
- Prompt should explain each tool in one short sentence.

## Domain / Access Flow
### Option A: User-Owned Domain/Subdomain
Recommended for normal production use.

Prompt for:
- domain/subdomain (example: `chat.example.com`)
- DNS provider
- Traefik network/email settings

Guide user to create DNS record:
- Type: `A` (or `CNAME` if appropriate)
- Host: chosen subdomain
- Value: VPS public IP (for A record)
- TTL: default

After DNS propagation:
- setup enables HTTPS route via Traefik
- app becomes available at `https://<domain>`

### Option B: Managed Domain (Paid)
If user does not want to manage DNS, offer managed domain routing:
- "Use my hosted domain option for `$5/month`."
- User confirms paid option and receives generated app URL/subdomain.
- Setup applies provider-specific routing config.

### Option C: VPS IP (Temporary)
For testing only:
- setup warns this is non-production
- user accesses app by IP
- user is encouraged to migrate to domain+HTTPS

## Setup Prompts (Recommended Order)
1. Confirm install/update directory.
2. Check Docker availability.
3. Check Codex CLI:
   - found + logged in -> continue
   - missing -> offer install
   - not logged in -> offer login
4. Check security baseline:
   - if `fail2ban` missing -> recommend install with copy/paste command
   - allow continue if user skips (with warning)
5. Optional CLIs (gh/supabase/google/cloudflare).
6. Access mode (domain, managed domain, or IP).
7. Domain + DNS instructions if needed.
8. Confirm summary and run deployment.

## Success Criteria
- User can complete setup without editing files manually.
- User can choose domain path that matches their comfort level.
- User reaches login screen and sends first message.
- Optional tools never block core install path.

## UX Copy Style
- Keep prompts short and plain.
- Always show a recommended default.
- Show risk labels clearly (for example IP mode / yolo mode).
- End every major step with clear "what happened" confirmation.
- Include security nudges without hard-blocking install (for example `fail2ban` recommendation).

## Future Improvements
- Interactive DNS helper per provider.
- "Check DNS now" loop before final deploy.
- Post-install verification script with pass/fail checklist.
