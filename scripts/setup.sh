#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

red() { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }

show_banner() {
  cat <<'BANNER'
         .-.
       ,'   '.
      /       \
     /         \
    /_,.-----.,_\
   ('_.-.---.-._')
    ()(o)   (o)()
    \(_.-(_)-._)/
   _/    '-'    \_
  / \_         _/ \
 |   /'-.___.-'\   |
|__/'._  ___  _.'\__|
(__)\__'|[-]|'__/(__)
    |           |
    |_____|_____\
    (____) (____)

                Welcome to AGENTMOBILE!
BANNER
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    red "Missing required command: $cmd"
    exit 1
  fi
}

CODEX_DETECTED_KIND=""
CODEX_BIN_PATH=""
CODEX_NODE_PATH=""
CODEX_NODE_MODULES_PATH=""
CODEX_AUTH_PATH=""

detect_codex_installation() {
  CODEX_DETECTED_KIND=""
  CODEX_BIN_PATH=""
  CODEX_NODE_PATH=""
  CODEX_NODE_MODULES_PATH=""
  CODEX_AUTH_PATH=""

  local candidate
  for candidate in /usr/bin/codex /usr/local/bin/codex /bin/codex; do
    if [ -x "$candidate" ]; then
      CODEX_DETECTED_KIND="global"
      CODEX_BIN_PATH="$candidate"
      break
    fi
  done

  if [ -z "$CODEX_BIN_PATH" ] && command -v codex >/dev/null 2>&1; then
    CODEX_DETECTED_KIND="path"
    CODEX_BIN_PATH="$(command -v codex)"
  fi

  if [ -z "$CODEX_BIN_PATH" ]; then
    return 1
  fi

  local resolved_bin
  resolved_bin="$(readlink -f "$CODEX_BIN_PATH" 2>/dev/null || printf '%s' "$CODEX_BIN_PATH")"

  local modules_guess=""
  if [[ "$resolved_bin" == */node_modules/@openai/codex/bin/codex.js ]]; then
    modules_guess="${resolved_bin%/@openai/codex/bin/codex.js}"
  elif command -v npm >/dev/null 2>&1; then
    modules_guess="$(npm root -g 2>/dev/null || true)"
  fi

  if [ -z "$modules_guess" ] || [ ! -d "$modules_guess/@openai/codex" ]; then
    return 1
  fi
  if [ ! -d "$modules_guess/@openai/codex/node_modules/@openai/codex-linux-x64" ]; then
    return 1
  fi

  local node_guess=""
  if command -v node >/dev/null 2>&1; then
    node_guess="$(command -v node)"
  fi
  if [ -z "$node_guess" ] || [ ! -x "$node_guess" ]; then
    return 1
  fi

  CODEX_NODE_MODULES_PATH="$(readlink -f "$modules_guess" 2>/dev/null || printf '%s' "$modules_guess")"
  CODEX_NODE_PATH="$(readlink -f "$node_guess" 2>/dev/null || printf '%s' "$node_guess")"
  CODEX_AUTH_PATH="$HOME/.codex"
  if [ -d "$CODEX_AUTH_PATH" ]; then
    CODEX_AUTH_PATH="$(readlink -f "$CODEX_AUTH_PATH" 2>/dev/null || printf '%s' "$CODEX_AUTH_PATH")"
  fi

  return 0
}

codex_cmd() {
  "$CODEX_BIN_PATH" "$@"
}

ensure_codex_installed() {
  if detect_codex_installation; then
    if [ "$CODEX_DETECTED_KIND" = "global" ]; then
      green "Using global Codex CLI: $CODEX_BIN_PATH"
    else
      green "Using Codex CLI from PATH: $CODEX_BIN_PATH"
    fi
    return 0
  fi

  yellow "Codex CLI was not found in global locations or PATH."
  local install_choice
  read -r -p "Install Codex CLI now? [Y/n]: " install_choice
  if [ -z "$install_choice" ] || [[ "$install_choice" =~ ^[Yy]$ ]]; then
    if [ ! -x "$ROOT_DIR/scripts/install-codex.sh" ]; then
      red "scripts/install-codex.sh is missing or not executable."
      exit 1
    fi
    "$ROOT_DIR/scripts/install-codex.sh"
  else
    red "Codex CLI is required. Re-run setup after installing Codex."
    exit 1
  fi

  if ! detect_codex_installation; then
    red "Codex CLI is still unavailable after install."
    exit 1
  fi

  green "Using Codex CLI: $CODEX_BIN_PATH"
}

ensure_codex_login() {
  if codex_cmd login status >/dev/null 2>&1; then
    return 0
  fi

  yellow "Codex is installed but not logged in."
  local login_choice
  read -r -p "Start Codex login now? [Y/n]: " login_choice
  if [ -z "$login_choice" ] || [[ "$login_choice" =~ ^[Yy]$ ]]; then
    codex_cmd login || true
  fi

  if ! codex_cmd login status >/dev/null 2>&1; then
    red "Codex login is required before continuing."
    yellow "Run: codex login   (or: codex login --device-auth)"
    exit 1
  fi
}

persist_codex_runtime_env() {
  set_env "CODEX_HOST_NODE_PATH" "$CODEX_NODE_PATH"
  set_env "CODEX_HOST_NODE_MODULES_PATH" "$CODEX_NODE_MODULES_PATH"
  set_env "CODEX_HOST_AUTH_PATH" "$CODEX_AUTH_PATH"
  set_env "CODEX_CONTAINER_NODE_PATH" "/usr/local/bin/node"
  set_env "CODEX_CONTAINER_NODE_MODULES_PATH" "/usr/local/lib/node_modules"
  set_env "CODEX_CONTAINER_AUTH_PATH" "/root/.codex"
  green "Wrote Codex runtime mount paths to .env"
}

set_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" .env; then
    sed -i "s|^${key}=.*|${key}=${value}|" .env
  else
    printf '%s=%s\n' "$key" "$value" >> .env
  fi
}

get_env_value() {
  local key="$1"
  grep -E "^${key}=" .env | sed "s/^${key}=//" | tail -n 1 || true
}

prompt_if_empty() {
  local key="$1"
  local prompt="$2"
  local current
  current="$(get_env_value "$key")"
  if [ -z "$current" ]; then
    read -r -p "$prompt: " current
    set_env "$key" "$current"
  fi
}

install_managed_traefik() {
  local network_name="$1"
  local acme_email
  acme_email="$(get_env_value "TRAEFIK_ACME_EMAIL")"
  if [ -z "$acme_email" ]; then
    read -r -p "Enter Traefik ACME email (for Let's Encrypt): " acme_email
    set_env "TRAEFIK_ACME_EMAIL" "$acme_email"
  fi
  if [ -z "$acme_email" ]; then
    red "Traefik ACME email is required."
    exit 1
  fi

  if [ ! -x "$ROOT_DIR/scripts/install-traefik.sh" ]; then
    red "scripts/install-traefik.sh is missing or not executable."
    exit 1
  fi

  TRAEFIK_NETWORK="$network_name" TRAEFIK_ACME_EMAIL="$acme_email" "$ROOT_DIR/scripts/install-traefik.sh"
}

choose_access_mode() {
  local mode
  mode="$(get_env_value "ACCESS_MODE")"
  if [ -z "$mode" ]; then
    yellow "Select access mode:"
    echo "  1) Traefik + HTTPS (recommended for production)"
    echo "  2) Direct IP mode (dev/test only, higher risk)"
    local selection
    while true; do
      read -r -p "Choose [1/2] (default 1): " selection
      selection="${selection:-1}"
      case "$selection" in
        1) mode="traefik"; break ;;
        2) mode="ip"; break ;;
        *) yellow "Invalid choice. Enter 1 or 2." ;;
      esac
    done
    set_env "ACCESS_MODE" "$mode"
  fi

  if [ "$mode" = "ip" ]; then
    yellow "WARNING: Direct IP mode is for dev/test only."
    yellow "It may reduce security and can weaken cookie/TLS protections."
    yellow "Use domain + HTTPS (Traefik mode) for production."
  fi
}

ensure_traefik_network() {
  local configured
  configured="$(get_env_value "TRAEFIK_NETWORK")"

  if [ -n "$configured" ] && docker network inspect "$configured" >/dev/null 2>&1; then
    green "Using TRAEFIK_NETWORK from .env: $configured"
    return 0
  fi

  if [ -n "$configured" ]; then
    yellow "Configured TRAEFIK_NETWORK '$configured' was not found."
  fi

  mapfile -t candidates < <(docker network ls --format '{{.Name}}' | grep -Ei 'traefik' || true)

  if [ "${#candidates[@]}" -eq 1 ]; then
    set_env "TRAEFIK_NETWORK" "${candidates[0]}"
    green "Auto-detected Traefik network: ${candidates[0]}"
    return 0
  fi

  if [ "${#candidates[@]}" -gt 1 ]; then
    yellow "Multiple Traefik-like networks found. Choose one:"
    local i=1
    for net in "${candidates[@]}"; do
      printf "  %d) %s\n" "$i" "$net"
      i=$((i + 1))
    done
    printf "  %d) Create a new network\n" "$i"

    local selection
    while true; do
      read -r -p "Select network number: " selection
      if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -lt "$i" ]; then
        set_env "TRAEFIK_NETWORK" "${candidates[$((selection - 1))]}"
        green "Using network: ${candidates[$((selection - 1))]}"
        return 0
      fi
      if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -eq "$i" ]; then
        break
      fi
      yellow "Invalid selection. Try again."
    done
  else
    yellow "No Traefik-like Docker network found."
  fi

  local install_choice
  read -r -p "Traefik not detected. Install managed Traefik now? [Y/n]: " install_choice
  if [ -z "$install_choice" ] || [[ "$install_choice" =~ ^[Yy]$ ]]; then
    local install_network
    local install_network_input
    install_network="${configured:-traefik-public}"
    read -r -p "Network name [$install_network]: " install_network_input
    install_network="${install_network_input:-$install_network}"
    set_env "TRAEFIK_NETWORK" "$install_network"
    install_managed_traefik "$install_network"
    green "Managed Traefik installed. Using network: $install_network"
    return 0
  fi

  local create_choice
  read -r -p "Create a new Traefik network now? [Y/n]: " create_choice
  if [ -z "$create_choice" ] || [[ "$create_choice" =~ ^[Yy]$ ]]; then
    local new_name
    read -r -p "Network name [traefik-public]: " new_name
    new_name="${new_name:-traefik-public}"

    if docker network inspect "$new_name" >/dev/null 2>&1; then
      yellow "Network '$new_name' already exists. Using it."
    else
      docker network create "$new_name" >/dev/null
      green "Created Docker network: $new_name"
    fi
    set_env "TRAEFIK_NETWORK" "$new_name"
    return 0
  fi

  red "A Traefik network is required. Re-run setup when available."
  exit 1
}

green "Checking prerequisites..."
show_banner
require_cmd docker
ensure_codex_installed

if ! docker info >/dev/null 2>&1; then
  red "Docker daemon is not running or not accessible to this user."
  exit 1
fi

ensure_codex_login

if [ ! -f .env.example ]; then
  red ".env.example is missing."
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  green "Created .env from .env.example"
fi

persist_codex_runtime_env

prompt_if_empty "APP_DOMAIN" "Enter APP_DOMAIN (example: chat.example.com)"
choose_access_mode

ACCESS_MODE="$(get_env_value "ACCESS_MODE")"
if [ "$ACCESS_MODE" = "traefik" ]; then
  ensure_traefik_network
fi

if [ -z "$(get_env_value "SESSION_SECRET")" ] || [ "$(get_env_value "SESSION_SECRET")" = "replace_with_long_random_secret" ]; then
  require_cmd openssl
  secret="$(openssl rand -hex 32)"
  set_env "SESSION_SECRET" "$secret"
  green "Generated SESSION_SECRET"
fi

if [ "$ACCESS_MODE" = "traefik" ]; then
  TRAEFIK_NETWORK="$(get_env_value "TRAEFIK_NETWORK")"
  if ! docker network inspect "$TRAEFIK_NETWORK" >/dev/null 2>&1; then
    red "Traefik network '$TRAEFIK_NETWORK' does not exist."
    yellow "Create or use the correct external network name, then rerun setup."
    exit 1
  fi
fi

if [ ! -f docker-compose.yml ] && [ ! -f compose.yml ] && [ ! -f compose.yaml ]; then
  yellow "No compose file found yet (docker-compose.yml/compose.yml/compose.yaml)."
  yellow "Prereq checks passed; add compose files and run: docker compose up -d"
  exit 0
fi

green "Starting containers..."
docker compose up -d

green "Setup complete. Open: https://$(get_env_value "APP_DOMAIN")"
