#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/patrickslom/agentmobile.git}"
BRANCH="${BRANCH:-master}"
INSTALL_DIR="${AGENTMOBILE_DIR:-$HOME/agentmobile}"

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

require_cmd git
require_cmd bash

green "AGENTMOBILE installer"
yellow "Repo: $REPO_URL"
yellow "Branch: $BRANCH"
yellow "Install dir: $INSTALL_DIR"

if [ -d "$INSTALL_DIR/.git" ]; then
  green "Existing install detected. Updating repository..."
  git -C "$INSTALL_DIR" fetch origin "$BRANCH"
  git -C "$INSTALL_DIR" checkout "$BRANCH"
  git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"
else
  if [ -e "$INSTALL_DIR" ] && [ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null || true)" ]; then
    red "Install directory exists and is not empty: $INSTALL_DIR"
    yellow "Set AGENTMOBILE_DIR to a different directory and re-run installer."
    exit 1
  fi

  green "Cloning repository..."
  git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

if [ ! -f "scripts/setup.sh" ]; then
  red "scripts/setup.sh not found after checkout."
  exit 1
fi

chmod +x scripts/setup.sh

green "Starting setup..."
exec bash ./scripts/setup.sh
