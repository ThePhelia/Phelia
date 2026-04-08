#!/usr/bin/env bash
set -euo pipefail

CONF_DIR="/config/qBittorrent"
CONF_FILE="$CONF_DIR/qBittorrent.conf"
QB_USER="${QBITTORRENT_USERNAME:-${QBIT_USERNAME:-${QB_USER:-admin}}}"
QB_PASS="${QBITTORRENT_PASSWORD:-${QBIT_PASSWORD:-${QB_PASS:-}}}"
QB_BOOTSTRAP_FORCE="${QB_BOOTSTRAP_FORCE:-false}"

is_true() {
  case "${1,,}" in
    1|true|yes|on)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

if [ -z "$QB_PASS" ]; then
  echo "[qb-bootstrap] QBITTORRENT_PASSWORD is empty; credentials unchanged (skipped)."
  exit 0
fi

had_config=false
if [ -f "$CONF_FILE" ]; then
  had_config=true
fi

if "$had_config" && ! is_true "$QB_BOOTSTRAP_FORCE"; then
  echo "[qb-bootstrap] Existing qBittorrent config found; credentials unchanged (skipped). Set QB_BOOTSTRAP_FORCE=true to rotate."
  exit 0
fi

mkdir -p "$CONF_DIR"
PBKDF2_LINE=$(python3 - <<'PY'
import base64, hashlib, os
password = os.environ.get('QB_PASS') or os.environ.get('QBIT_PASSWORD') or ''
password = (
    os.environ.get('QBITTORRENT_PASSWORD')
    or os.environ.get('QBIT_PASSWORD')
    or os.environ.get('QB_PASS')
    or ''
)
iterations = 100000
salt = os.urandom(16)
digest = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, iterations)
print(f"@ByteArray({iterations}:{base64.b64encode(salt).decode()}:{base64.b64encode(digest).decode()})")
PY
)

cat > "$CONF_FILE" <<EOF_CONF
[Preferences]
WebUI\\Enabled=true
WebUI\\Address=*
WebUI\\Port=8080
WebUI\\Username=${QB_USER}
WebUI\\Password_PBKDF2=${PBKDF2_LINE}
EOF_CONF

chmod 600 "$CONF_FILE"

if "$had_config"; then
  echo "[qb-bootstrap] Rotated qBittorrent WebUI credentials in persisted config (QB_BOOTSTRAP_FORCE=true)."
else
  echo "[qb-bootstrap] Initialized qBittorrent WebUI credentials in persisted config."
fi
