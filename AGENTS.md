# Repository Agent Notes

## Frontend Rebuild Modes

This repo supports two frontend rebuild paths when editing directly on the production host.

Default:

```bash
./scripts/rebuild-front.sh
```

This is the `quick` path:
- uses `docker-compose.front-quick.yml`
- runs `codexchat_front` with `next dev`
- bind-mounts `./codexchat_front` into the container
- keeps `node_modules` and `.next` in named Docker volumes
- avoids the slow production image rebuild loop for normal UI edits

Full rebuild:

```bash
./scripts/rebuild-front.sh full
```

This is the strict production-style path:
- uses the normal `docker-compose.yml` frontend build
- runs the full optimized `next build` image flow
- use it for dependency changes, build-config changes, and before higher-confidence verification

## Recommended Usage

- Use `quick` for routine component, CSS, layout, and client-side logic edits.
- Use `full` after changes to frontend dependencies, Dockerfile behavior, or when validating the production build path.
- Backend rebuilds are already relatively cheap compared with frontend production builds.
