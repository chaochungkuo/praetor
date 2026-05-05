#!/usr/bin/env sh
set -eu

REPO_URL="${PRAETOR_REPO_URL:-https://github.com/chaochungkuo/praetor.git}"
REPO_BRANCH="${PRAETOR_REPO_BRANCH:-main}"
PRAETOR_HOME="${PRAETOR_HOME:-$HOME/.praetor}"
INSTALL_DIR="${PRAETOR_INSTALL_DIR:-$PRAETOR_HOME/praetor}"
DATA_DIR="${PRAETOR_DATA_DIR:-$PRAETOR_HOME/data}"
WORKSPACE_DIR="${PRAETOR_WORKSPACE_DIR:-$HOME/praetor-workspace}"
APP_PORT="${PRAETOR_APP_PORT:-9741}"
APP_HOST="${PRAETOR_APP_BIND_HOST:-127.0.0.1}"

log() {
  printf '%s\n' "$*"
}

fail() {
  printf 'Praetor install failed: %s\n' "$*" >&2
  exit 1
}

need_command() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required."
}

compose() {
  docker compose "$@"
}

random_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
  else
    fail "openssl or python3 is required to generate secure secrets."
  fi
}

open_url() {
  url="$1"
  if command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
  fi
}

need_command docker
docker info >/dev/null 2>&1 || fail "Docker is not running. Start Docker Desktop or Docker Engine, then run this command again."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required."

mkdir -p "$PRAETOR_HOME" "$DATA_DIR" "$WORKSPACE_DIR"
chmod 700 "$PRAETOR_HOME" "$DATA_DIR" "$WORKSPACE_DIR" 2>/dev/null || true

if [ -d "$INSTALL_DIR/.git" ]; then
  need_command git
  log "Updating Praetor source in $INSTALL_DIR"
  git -C "$INSTALL_DIR" fetch --depth 1 origin "$REPO_BRANCH"
  git -C "$INSTALL_DIR" checkout "$REPO_BRANCH"
  git -C "$INSTALL_DIR" reset --hard "origin/$REPO_BRANCH"
else
  need_command git
  rm -rf "$INSTALL_DIR"
  log "Installing Praetor into $INSTALL_DIR"
  git clone --depth 1 --branch "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi

SESSION_SECRET="$(random_secret)"
SETUP_TOKEN="$(random_secret)"

cat > "$INSTALL_DIR/.env" <<EOF
PRAETOR_ENV=local
PRAETOR_APP_BIND_HOST=$APP_HOST
PRAETOR_APP_PORT=$APP_PORT
PRAETOR_DATA_DIR=$DATA_DIR
PRAETOR_WORKSPACE_DIR=$WORKSPACE_DIR
PRAETOR_SESSION_SECRET=$SESSION_SECRET
PRAETOR_SETUP_TOKEN=$SETUP_TOKEN
PRAETOR_REQUIRE_LOGIN=true
PRAETOR_SECURE_COOKIE=false
PRAETOR_DEBUG_ROUTES=false
EOF
chmod 600 "$INSTALL_DIR/.env" 2>/dev/null || true

log "Starting Praetor..."
(cd "$INSTALL_DIR" && compose -f compose.app.yaml up --build -d)

SETUP_URL="http://$APP_HOST:$APP_PORT/app/praetor?setup_token=$SETUP_TOKEN"

log ""
log "Praetor is running."
log "Open this first-run setup URL:"
log "$SETUP_URL"
log ""
log "Private data: $DATA_DIR"
log "Workspace:    $WORKSPACE_DIR"
log ""
log "To update:    $INSTALL_DIR/scripts/update.sh"
log "To uninstall: $INSTALL_DIR/scripts/uninstall.sh"

open_url "$SETUP_URL"
