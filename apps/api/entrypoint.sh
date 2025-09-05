#!/usr/bin/env bash
set -euo pipefail

cd /app
export PYTHONPATH=/app

# Простой ожидатель Postgres (на всякий случай, healthcheck у нас уже есть)
echo "Running Alembic migrations..."
alembic upgrade head || { echo "Alembic failed"; exit 1; }

echo "Starting Gunicorn..."
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:${API_PORT:-8000} \
  --access-logfile - \
  --error-logfile - \
  --workers ${GUNICORN_WORKERS:-2} \
  --threads ${GUNICORN_THREADS:-4} \
  --timeout ${GUNICORN_TIMEOUT:-120}

