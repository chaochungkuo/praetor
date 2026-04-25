#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT="${1:-$(pwd)}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${ROOT}/backups"
ARCHIVE="${BACKUP_DIR}/praetor-backup-${STAMP}.tar.gz"

mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}" 2>/dev/null || true

tar -czf "${ARCHIVE}" \
  -C "${ROOT}" \
  workspace \
  data \
  config 2>/dev/null || true
chmod 600 "${ARCHIVE}" 2>/dev/null || true

echo "${ARCHIVE}"
