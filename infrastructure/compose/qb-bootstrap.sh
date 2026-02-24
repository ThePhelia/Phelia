#!/usr/bin/env bash
set -euo pipefail

CONF_DIR="/config/qBittorrent"
CONF_FILE="$CONF_DIR/qBittorrent.conf"
QB_USER="${QB_USER:-${QBIT_USERNAME:-admin}}"
QB_PASS="${QB_PASS:-${QBIT_PASSWORD:-}}"

if [ -z "$QB_PASS" ]; then
  echo "[qb-bootstrap] QB_PASS/QBIT_PASSWORD is empty; skipping bootstrap to avoid invalid config."
  exit 0
fi

if [ -f "$CONF_FILE" ]; then
  echo "[qb-bootstrap] Existing qBittorrent config found; leaving credentials unchanged."
  exit 0
fi

mkdir -p "$CONF_DIR"
PBKDF2_LINE=$(python3 - <<'PY'
import base64, hashlib, os
password = os.environ.get('QB_PASS') or os.environ.get('QBIT_PASSWORD') or ''
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
echo "[qb-bootstrap] Initialized qBittorrent WebUI credentials in persisted config."
