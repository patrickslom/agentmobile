# Repository Agent Notes

## Required Reading

Agents must read `docs/RULES.md` before starting work in this repository.

## Frontend Rebuild Rule

This repo supports two frontend rebuild paths when editing directly on the production host.

When changing frontend code on this host, you must use the quick rebuild path by default.

Default command:

```bash
./scripts/rebuild-front.sh
```

This is the required default `quick` path:
- uses `docker-compose.front-quick.yml`
- runs `frontend` with `next dev`
- bind-mounts `./frontend` into the container
- keeps `node_modules` and `.next` in named Docker volumes
- avoids the slow production image rebuild loop for normal UI edits

Only use the full production rebuild when the user explicitly asks for it, or when the change affects:
- frontend dependencies
- Dockerfile or compose behavior
- build-time environment or build config
- production-only verification

Full rebuild command:

```bash
./scripts/rebuild-front.sh full
```

This is the strict production-style path:
- uses the normal `docker-compose.yml` frontend build
- runs the full optimized `next build` image flow
- use it for dependency changes, build-config changes, and before higher-confidence verification

Do not use `docker compose up -d --build frontend` directly for routine frontend edits.
If you choose the full rebuild path, state the reason explicitly before running it.

## Database Change Rule

If a change adds, removes, or alters database schema or migration files, the same run must also:
- apply the migration to the live database
- rebuild and restart any affected long-running services that use that schema, at minimum `backend` and `worker`
- verify the updated schema is live before considering the task complete

Do not stop after editing model or Alembic files when database-affecting changes are part of the work.
