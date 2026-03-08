#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-quick}"

case "$MODE" in
  quick)
    echo "Starting quick front-end rebuild (bind-mounted source + next dev)..."
    docker compose -f docker-compose.yml -f docker-compose.front-quick.yml up -d --force-recreate codexchat_front
    ;;
  full)
    echo "Starting full front-end rebuild (production image build)..."
    docker compose -f docker-compose.yml up -d --build --force-recreate codexchat_front
    ;;
  *)
    echo "Usage: scripts/rebuild-front.sh [quick|full]" >&2
    exit 1
    ;;
esac
