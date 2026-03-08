# Integrations Plan

## Goal
Support optional external integrations for storage/database while keeping local VPS defaults.

## Default Behavior (Fallback)
If no integration env vars are configured:
- database uses current self-hosted Postgres setup
- files use current VPS/local storage path

This preserves current out-of-the-box behavior.

## Optional Integration 1: Cloudflare R2 (File Storage)
If user provides R2 credentials in `.env`, store uploaded files in R2 instead of local VPS disk.

### Env Vars (Proposed)
- `STORAGE_PROVIDER=local|r2` (default: `local`)
- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET`
- `R2_REGION` (optional, often `auto`)
- `R2_ENDPOINT` (S3-compatible endpoint)
- `R2_PUBLIC_BASE_URL` (optional, for direct/public URL patterns)

### Behavior
- `local`: existing file flow unchanged.
- `r2`: writes/reads/deletes go through R2 adapter.
- keep metadata and ownership records in app database.

## Optional Integration 2: Supabase
Allow users to connect Supabase via env vars.

Two practical modes:
- DB-only mode: use Supabase Postgres as `DATABASE_URL`.
- Full Supabase mode (later/optional): also support Supabase Storage and/or auth integration.

### Env Vars (Proposed)
- `DATABASE_PROVIDER=local|supabase` (default: `local`)
- `DATABASE_URL` (when using Supabase Postgres, point this to Supabase connection string)
- `SUPABASE_URL` (optional for future API/storage/auth calls)
- `SUPABASE_ANON_KEY` (optional)
- `SUPABASE_SERVICE_ROLE_KEY` (optional, server-side only)

### Behavior
- `local`: existing self-hosted Postgres behavior.
- `supabase`: app connects to Supabase Postgres using `DATABASE_URL`.

## Provider Selection Rules
- Validate env at startup.
- If provider is selected but required vars are missing:
  - log clear error
  - fail fast or fallback based on strictness setting

Recommended strictness:
- production: fail fast on invalid selected provider
- dev: optional warning + local fallback

## Implementation Shape
- Introduce provider interfaces:
  - `StorageProvider` with `put/get/delete/presign`
  - `DatabaseProvider` (or simpler: database URL source policy)
- Implement adapters:
  - `LocalStorageProvider` (existing behavior)
  - `R2StorageProvider`
- Keep routing/business logic provider-agnostic.

## Security Notes
- Never expose secret keys to frontend.
- Use server-side credentials only.
- Document least-privilege IAM/policy for R2 keys.
- Add startup checks that confirm bucket/db reachability.

## Migration and Backward Compatibility
- Existing installations require no changes.
- Users can opt in by setting env vars and restarting services.
- Existing local files remain valid unless user explicitly migrates.

## Future Enhancements
- one-time migration tool: local files -> R2
- selectable per-project storage backend
- optional Supabase Storage adapter
