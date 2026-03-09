#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STACK_DIR="$ROOT_DIR/.agentmobile/traefik"

red() { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    red "Missing required command: $cmd"
    exit 1
  fi
}

NETWORK="${TRAEFIK_NETWORK:-traefik-public}"
ACME_EMAIL="${TRAEFIK_ACME_EMAIL:-}"

while [ $# -gt 0 ]; do
  case "$1" in
    --network)
      NETWORK="$2"
      shift 2
      ;;
    --email)
      ACME_EMAIL="$2"
      shift 2
      ;;
    *)
      red "Unknown argument: $1"
      exit 1
      ;;
  esac
done

require_cmd docker

if ! docker info >/dev/null 2>&1; then
  red "Docker daemon is not running or not accessible to this user."
  exit 1
fi

if [ -z "$ACME_EMAIL" ]; then
  read -r -p "Enter Traefik ACME email (for Let's Encrypt): " ACME_EMAIL
fi

if [ -z "$ACME_EMAIL" ]; then
  red "ACME email is required to configure Let's Encrypt."
  exit 1
fi

mkdir -p "$STACK_DIR"

if ! docker network inspect "$NETWORK" >/dev/null 2>&1; then
  docker network create "$NETWORK" >/dev/null
  green "Created Docker network: $NETWORK"
else
  yellow "Using existing Docker network: $NETWORK"
fi

cat > "$STACK_DIR/.env" <<ENV
TRAEFIK_NETWORK=$NETWORK
TRAEFIK_ACME_EMAIL=$ACME_EMAIL
ENV

cat > "$STACK_DIR/docker-compose.yml" <<'COMPOSE'
services:
  traefik:
    image: traefik:v3.1
    container_name: agentmobile_traefik
    restart: unless-stopped
    command:
      - --api.dashboard=true
      - --providers.docker=true
      - --providers.docker.exposedbydefault=false
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
      - --certificatesresolvers.le.acme.email=${TRAEFIK_ACME_EMAIL}
      - --certificatesresolvers.le.acme.storage=/letsencrypt/acme.json
      - --certificatesresolvers.le.acme.httpchallenge=true
      - --certificatesresolvers.le.acme.httpchallenge.entrypoint=web
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./acme.json:/letsencrypt/acme.json
    networks:
      - traefik-public

networks:
  traefik-public:
    external: true
    name: ${TRAEFIK_NETWORK}
COMPOSE

if [ ! -f "$STACK_DIR/acme.json" ]; then
  touch "$STACK_DIR/acme.json"
fi
chmod 600 "$STACK_DIR/acme.json"

( cd "$STACK_DIR" && docker compose up -d )

green "Managed Traefik installed and running."
green "Stack dir: $STACK_DIR"
