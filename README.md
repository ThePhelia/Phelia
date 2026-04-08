# Phelia

Phelia is a self-hosted media discovery and download orchestration project.
It combines a FastAPI backend, Celery workers, PostgreSQL/Redis, qBittorrent, Prowlarr, and a React/Vite web UI.

## Current status

Active development. The core path is:

- browse/discover media in the web UI
- enrich metadata in the API
- search configured indexers (Prowlarr)
- submit downloads to qBittorrent

## Tech stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Alembic, Celery
- **Frontend:** React 18, TypeScript, Vite, Tailwind
- **Infra:** Docker Compose, PostgreSQL, Redis, qBittorrent, Prowlarr

## Repository layout

```text
apps/
  api/        FastAPI app, workers, DB models, tests
  web/        React/Vite frontend
infrastructure/
  compose/    docker-compose stack and helper scripts
  env/        web env files used by compose
scripts/
  dev_smoke.sh  dockerized API smoke check
```

## Setup

### Prerequisites

- Docker + Docker Compose
- (Optional for local non-docker development) Python 3.12 and Node 18+

### Start the full stack

```bash
make up
```

API default URL: `http://localhost:8121`  
Web default URL: `http://localhost:80`

Stop services:

```bash
make down
```

## Environment variables

Primary compose defaults are in `infrastructure/compose/.env`.

Common variables:

- `API_PORT` (default `8121`)
- `WEB_PORT` (default `80`)
- `VITE_API_BASE` (default `/api/v1`)
- `VITE_WS_BASE` (default `/ws`)
- `QBITTORRENT_USERNAME` / `QBITTORRENT_PASSWORD`
- `PROWLARR_URL` / `PROWLARR_API_KEY`

Backend runtime settings also support:

- `DATABASE_URL`, `REDIS_URL`
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `APP_SECRET`
- provider keys like `TMDB_API_KEY`, `OMDB_API_KEY`, `DISCOGS_TOKEN`, `LASTFM_API_KEY`

### Music discovery provider notes

- `LASTFM_API_KEY` is required for reliable music search and tag/top discovery rails.
- Last.fm shared secret is **not** required for read-only discovery/search flows.
- `LISTENBRAINZ_TOKEN` is optional and used for similar-artist/personalization style features, not primary album search.

Use `.env.example` as the baseline for non-compose local runs.

## Development commands

```bash
make up           # start stack
make down         # stop stack
make logs         # compose logs
make api-logs     # API logs only
make web-logs     # Web logs only
./scripts/dev_smoke.sh
```

Backend targeted tests:

```bash
pytest -q apps/api/tests/test_health.py apps/api/tests/test_metadata_classifier.py
```

Frontend:

```bash
cd apps/web
npm ci
npm run dev
npm run test
```

## Build / run details

- Backend container runs `apps/api/entrypoint.sh`, applies DB migration, then starts uvicorn.
- Worker/beat run Celery from `app.services.jobs.tasks.celery_app`.
- Web image builds the Vite app and serves it via nginx (`apps/web/nginx.conf`).

## Deployment notes

- The included compose stack is development-oriented but production-shaped.
- Persisted volumes contain DB data, Redis data, qBittorrent config, Prowlarr config, and encrypted app secrets.
- Do **not** commit real credentials in env files.

## Known limitations

- CI currently runs a focused backend subset, not the full integration matrix.
- Some discovery and provider features depend on external APIs and configured keys.
