#!/usr/bin/env sh
set -eu

PRAETOR_HOME="${PRAETOR_HOME:-$HOME/.praetor}"
INSTALL_DIR="${PRAETOR_INSTALL_DIR:-$PRAETOR_HOME/praetor}"
REPO_BRANCH="${PRAETOR_REPO_BRANCH:-main}"

fail() {
  printf 'Praetor update failed: %s\n' "$*" >&2
  exit 1
}

[ -d "$INSTALL_DIR/.git" ] || fail "Praetor is not installed at $INSTALL_DIR."
command -v docker >/dev/null 2>&1 || fail "docker is required."
command -v git >/dev/null 2>&1 || fail "git is required."
docker info >/dev/null 2>&1 || fail "Docker is not running."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required."

git -C "$INSTALL_DIR" fetch --depth 1 origin "$REPO_BRANCH"
git -C "$INSTALL_DIR" checkout "$REPO_BRANCH"
git -C "$INSTALL_DIR" reset --hard "origin/$REPO_BRANCH"

cd "$INSTALL_DIR"
docker compose -f compose.app.yaml up --build -d

printf '%s\n' "Praetor updated and restarted."
