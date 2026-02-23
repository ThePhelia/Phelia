#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infrastructure/compose/docker-compose.yml"
API_HEALTH="http://localhost:8000/api/v1/healthz"
API_CHECK="http://localhost:8000/api/v1/discover/movie"

cleanup() {
  docker compose -f "$COMPOSE_FILE" down --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[dev_smoke] Building API service..."
docker compose -f "$COMPOSE_FILE" build api >/dev/null

echo "[dev_smoke] Starting stack..."
docker compose -f "$COMPOSE_FILE" up -d db redis qbittorrent api >/dev/null

echo "[dev_smoke] Waiting for API health..."
until curl -fsS "$API_HEALTH" >/dev/null; do
  sleep 2
  echo "  api not ready yet..."
done

API_STATUS=$(curl -fsS -o /dev/null -w "%{http_code}" "$API_CHECK" || true)
printf "API metadata endpoint: %s\n" "$API_STATUS"

if [[ "$API_STATUS" == "200" || "$API_STATUS" == "400" ]]; then
  echo "[dev_smoke] Smoke test succeeded."
else
  echo "[dev_smoke] Smoke test failed." >&2
  exit 1
fi
