#!/usr/bin/env sh
set -eu

PRAETOR_HOME="${PRAETOR_HOME:-$HOME/.praetor}"
INSTALL_DIR="${PRAETOR_INSTALL_DIR:-$PRAETOR_HOME/praetor}"
ENV_FILE="$INSTALL_DIR/.env"
CONFIG_DIR="$INSTALL_DIR/config"
BRIDGE_CONFIG="$CONFIG_DIR/praetor-execd.yaml"
BRIDGE_LOG="$INSTALL_DIR/praetor-execd.log"
BRIDGE_PID="$INSTALL_DIR/praetor-execd.pid"
BRIDGE_URL="${PRAETOR_BRIDGE_BASE_URL:-http://host.docker.internal:9417}"
BRIDGE_PORT="${PRAETOR_EXECUTOR_BRIDGE_PORT:-9417}"
APP_PROJECT="${PRAETOR_COMPOSE_PROJECT:-praetor-app}"
APP_COMPOSE_FILE="${PRAETOR_COMPOSE_FILE:-compose.app.yaml}"

log() {
  printf '%s\n' "$*"
}

fail() {
  printf 'Praetor Codex executor setup failed: %s\n' "$*" >&2
  exit 1
}

need_command() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required."
}

random_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 48 | tr '+/' '-_' | tr -d '=\n'
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c 'import secrets; print(secrets.token_urlsafe(36))'
  else
    fail "openssl or python3 is required to generate a bridge token."
  fi
}

env_value() {
  key="$1"
  [ -f "$ENV_FILE" ] || return 0
  sed -n "s/^$key=//p" "$ENV_FILE" | tail -n 1
}

upsert_env() {
  key="$1"
  value="$2"
  touch "$ENV_FILE"
  if grep -q "^$key=" "$ENV_FILE"; then
    tmp="$ENV_FILE.tmp"
    sed "s|^$key=.*|$key=$value|" "$ENV_FILE" > "$tmp"
    mv "$tmp" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
  chmod 600 "$ENV_FILE" 2>/dev/null || true
}

wait_for_bridge() {
  token="$1"
  i=0
  while [ "$i" -lt 30 ]; do
    if curl -fsS -H "Authorization: Bearer $token" "http://127.0.0.1:$BRIDGE_PORT/health" >/dev/null 2>&1; then
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  return 1
}

[ -d "$INSTALL_DIR" ] || fail "Praetor is not installed at $INSTALL_DIR."
[ -f "$ENV_FILE" ] || fail "Missing $ENV_FILE. Run scripts/install.sh first."
need_command docker
need_command pixi
need_command codex
need_command curl
need_command python3

if ! codex login status 2>&1 | grep -qi "Logged in"; then
  fail "Codex is not logged in. Run 'codex login' first and choose Sign in with ChatGPT."
fi

WORKSPACE_DIR="$(env_value PRAETOR_WORKSPACE_DIR)"
[ -n "$WORKSPACE_DIR" ] || WORKSPACE_DIR="$HOME/praetor-workspace"
DATA_DIR="$(env_value PRAETOR_DATA_DIR)"
[ -n "$DATA_DIR" ] || DATA_DIR="$PRAETOR_HOME/data"
CODEX_COMMAND="$(command -v codex)"
BRIDGE_TOKEN="$(env_value PRAETOR_BRIDGE_TOKEN)"
[ -n "$BRIDGE_TOKEN" ] || BRIDGE_TOKEN="$(random_secret)"

mkdir -p "$CONFIG_DIR" "$WORKSPACE_DIR/.praetor/bridge-logs"
chmod 700 "$WORKSPACE_DIR" 2>/dev/null || true

upsert_env PRAETOR_BRIDGE_BASE_URL "$BRIDGE_URL"
upsert_env PRAETOR_BRIDGE_TOKEN "$BRIDGE_TOKEN"
upsert_env PRAETOR_HOST_WORKSPACE_ROOT "$WORKSPACE_DIR"

SETTINGS_FILE="$DATA_DIR/state/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
  python3 - "$SETTINGS_FILE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
settings = json.loads(path.read_text(encoding="utf-8"))
workspace = settings.setdefault("workspace", {})
workspace["root"] = "/app/workspace"
workspace["permissions"] = {
    "allow_read": ["/app/workspace"],
    "allow_write": [
        "/app/workspace/Projects",
        "/app/workspace/Wiki",
        "/app/workspace/Decisions",
        "/app/workspace/Missions",
    ],
    "deny_write": [
        "/app/workspace/Archive",
        "/app/workspace/Finance/Locked",
    ],
}
path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
fi

cat > "$BRIDGE_CONFIG" <<EOF
server:
  host: 127.0.0.1
  port: $BRIDGE_PORT
  auth_token: env:PRAETOR_EXECUTOR_BRIDGE_TOKEN

paths:
  host_workspace_root: $WORKSPACE_DIR
  allowed_roots:
    - $WORKSPACE_DIR
  deny_roots:
    - $WORKSPACE_DIR/.praetor/secrets

executors:
  codex:
    enabled: true
    command: $CODEX_COMMAND
    args: []
    healthcheck: ["$CODEX_COMMAND", "exec", "--help"]
    requires_login: true
    supports_noninteractive_batch: true
    supports_cancel: true

  claude_code:
    enabled: false
    command: claude
    args: []
    healthcheck: ["claude", "--help"]
    requires_login: true
    supports_noninteractive_batch: true
    supports_cancel: true

runtime:
  max_concurrent_runs: 1
  default_timeout_seconds: 1800
  max_event_buffer: 5000
  persist_run_logs: true
  log_dir: $WORKSPACE_DIR/.praetor/bridge-logs
EOF

if [ "$(uname -s)" = "Darwin" ] && command -v launchctl >/dev/null 2>&1; then
  PLIST_DIR="$HOME/Library/LaunchAgents"
  PLIST="$PLIST_DIR/com.praetor.execd.plist"
  mkdir -p "$PLIST_DIR"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.praetor.execd</string>
  <key>ProgramArguments</key>
  <array>
    <string>$(command -v pixi)</string>
    <string>run</string>
    <string>bridge-serve</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$INSTALL_DIR</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PRAETOR_EXECD_CONFIG</key>
    <string>$BRIDGE_CONFIG</string>
    <key>PRAETOR_EXECUTOR_BRIDGE_TOKEN</key>
    <string>$BRIDGE_TOKEN</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$BRIDGE_LOG</string>
  <key>StandardErrorPath</key>
  <string>$BRIDGE_LOG</string>
</dict>
</plist>
EOF
  launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
else
  if [ -f "$BRIDGE_PID" ] && kill -0 "$(cat "$BRIDGE_PID")" >/dev/null 2>&1; then
    kill "$(cat "$BRIDGE_PID")" >/dev/null 2>&1 || true
  fi
  (
    cd "$INSTALL_DIR"
    PRAETOR_EXECD_CONFIG="$BRIDGE_CONFIG" PRAETOR_EXECUTOR_BRIDGE_TOKEN="$BRIDGE_TOKEN" \
      nohup pixi run bridge-serve > "$BRIDGE_LOG" 2>&1 &
    echo $! > "$BRIDGE_PID"
  )
fi

if ! wait_for_bridge "$BRIDGE_TOKEN"; then
  fail "Bridge did not become healthy. Check $BRIDGE_LOG."
fi

(cd "$INSTALL_DIR" && docker compose -f "$APP_COMPOSE_FILE" --env-file "$ENV_FILE" -p "$APP_PROJECT" up -d --force-recreate)

log "Codex executor is configured."
log "Bridge:    http://127.0.0.1:$BRIDGE_PORT"
log "Workspace: $WORKSPACE_DIR"
log "Open Praetor -> Models & API -> Local subscription tool -> Codex CLI -> Test connection."
