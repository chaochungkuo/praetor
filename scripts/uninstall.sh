#!/usr/bin/env sh
set -eu

PRAETOR_HOME="${PRAETOR_HOME:-$HOME/.praetor}"
INSTALL_DIR="${PRAETOR_INSTALL_DIR:-$PRAETOR_HOME/praetor}"
DATA_DIR="${PRAETOR_DATA_DIR:-$PRAETOR_HOME/data}"
WORKSPACE_DIR="${PRAETOR_WORKSPACE_DIR:-$HOME/praetor-workspace}"

if [ -d "$INSTALL_DIR" ] && command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  (cd "$INSTALL_DIR" && docker compose -f compose.app.yaml down --remove-orphans) || true
fi

rm -rf "$INSTALL_DIR"

if [ "${1:-}" = "--purge" ]; then
  rm -rf "$DATA_DIR" "$WORKSPACE_DIR"
  printf '%s\n' "Praetor app, state, and workspace removed."
else
  printf '%s\n' "Praetor app removed. Your data and workspace were kept:"
  printf '%s\n' "  State:     $DATA_DIR"
  printf '%s\n' "  Workspace: $WORKSPACE_DIR"
  printf '%s\n' "Run with --purge to remove them too."
fi
