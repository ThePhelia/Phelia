# Cleanup Inventory

## KEEP
- `apps/api` – FastAPI backend and Celery workers
- `apps/web` – Vite/React frontend (needs relocation later)
- `services/metadata-proxy` – shared metadata facade
- `plugins/` – shipped plugin sources & tests
- `scripts/dev_smoke.sh` – local docker smoke stack (now points to `infrastructure/compose/docker-compose.yml`)
- `tests/` – existing backend suite plus new smoke coverage
- `makefile` & `pyproject.toml` – build/test plumbing
- `deploy/.env` – shared dotenv consumed by compose (contains provider keys; leave in place)

## REWRITE / TODO
- Align frontend location with top-level `frontend/` target path without breaking docker builds
- Document plugin packaging workflow under `docs/`
- Evaluate moving core service from `apps/api` into `apps/core` once imports allow

## ARCHIVE CANDIDATES
- Heavy CI workflow `.github/workflows/ci.yml` (moved to `archive/ci/ci.yml`)
- Any alternative compose files or experimental envs if found in future sweeps
- Redundant placeholder directories once services are migrated for real

## DELETE (Generated / Cache)
- `apps/web/node_modules/` (install-time artefact; `.gitignore` updated)
- `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` and similar build caches
