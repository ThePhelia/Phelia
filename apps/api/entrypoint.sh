#!/usr/bin/env bash
set -euo pipefail
cd /app
export PYTHONPATH=/app

echo "[entrypoint] running alembic migrations..."
alembic upgrade head
echo "[entrypoint] migrations done"

echo "[entrypoint] starting gunicorn..."
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:${API_PORT:-8000} \
  --access-logfile - \
  --error-logfile - \
  --workers ${GUNICORN_WORKERS:-2} \
  --threads ${GUNICORN_THREADS:-4} \
  --timeout ${GUNICORN_TIMEOUT:-120}

