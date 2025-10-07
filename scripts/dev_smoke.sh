#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/deploy/docker-compose.yml"
PROXY_URL="http://localhost:8080/health"
API_HEALTH="http://localhost:8000/api/v1/healthz"
API_CHECK="http://localhost:8000/api/v1/discover/movie"

cleanup() {
  docker compose -f "$COMPOSE_FILE" down --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[dev_smoke] Building metadata services..."
docker compose -f "$COMPOSE_FILE" build metadata-proxy api >/dev/null

echo "[dev_smoke] Starting stack..."
docker compose -f "$COMPOSE_FILE" up -d metadata-proxy db redis qbittorrent api >/dev/null

echo "[dev_smoke] Waiting for metadata proxy health..."
until curl -fsS "$PROXY_URL" >/dev/null; do
  sleep 2
  echo "  proxy not ready yet..."
done

echo "[dev_smoke] Waiting for API health..."
until curl -fsS "$API_HEALTH" >/dev/null; do
  sleep 2
  echo "  api not ready yet..."
done
PROXY_STATUS=$(curl -fsS -o /dev/null -w "%{http_code}" "$PROXY_URL" || true)
API_STATUS=$(curl -fsS -o /dev/null -w "%{http_code}" "$API_CHECK" || true)

printf "Metadata proxy health: %s\n" "$PROXY_STATUS"
printf "API metadata endpoint: %s\n" "$API_STATUS"

if [[ "$PROXY_STATUS" == "200" && "$API_STATUS" == "200" ]]; then
  echo "[dev_smoke] Smoke test succeeded."
else
  echo "[dev_smoke] Smoke test failed." >&2
  exit 1
fi
