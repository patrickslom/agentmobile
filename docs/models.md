# Model Selection Findings

Date reviewed: 2026-03-08

## Short answer

Yes, `agentmobile` can support user-selectable models, but the current app does not expose that capability.

## Current app state

The current `agentmobile` implementation does not expose model selection in the UI, API, database settings, or websocket payloads.

- The runtime launches `codex app-server --listen stdio://` with no explicit `--model` flag or config override.
- Chat turns send `approvalPolicy`, `sandboxPolicy`, and `input` to `turn/start`, but no `model`.
- The websocket flow only derives sandbox mode from `execution_mode_default`.
- The persisted settings model only contains execution mode, upload, heartbeat, and theme defaults.
- The frontend settings page only knows about those same fields.

## Upstream Codex capability

The underlying Codex runtime does support model selection.

- Local CLI help shows `codex` and `codex exec` support `-m, --model <MODEL>`.
- `codex app-server` supports config overrides via `-c`, including `model="..."`.
- The local app-server JSON schema confirms support for:
  - `thread/start.model`
  - `thread/resume.model`
  - `turn/start.model`
  - `model/list`

This means model selection is supported by the runtime even though `agentmobile` does not currently pass or persist it.

## Current default in this environment

In this environment, `/root/.codex/config.toml` currently sets:

```toml
model = "gpt-5.4"
```

Because `agentmobile` does not pass an explicit model today, it will likely inherit that default from the mounted Codex configuration.

## What would be needed

If model selection is added to the app, the clean product choices are:

- global admin default model
- per-user default model
- per-conversation model
- per-turn override

The runtime is capable of supporting per-conversation or per-turn model selection. The missing pieces are app-level persistence, API or websocket fields, and UI controls.

## Evidence reviewed

Repository files:

- `backend/app/domains/codex/runtime.py`
- `backend/app/domains/chat/websocket.py`
- `backend/app/db/models.py`
- `backend/app/domains/settings/router.py`
- `frontend/components/settings/settings-page-client.tsx`
- `docker-compose.yml`

Local runtime evidence:

- `codex --help`
- `codex exec --help`
- `codex app-server --help`
- generated local schema from `codex app-server generate-json-schema`

Official docs checked:

- https://developers.openai.com/codex/config-advanced/
- https://developers.openai.com/codex/app-server
