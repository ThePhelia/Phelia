# Phelia

Phelia is a modular media automation stack that mirrors the capabilities of Sonarr/Radarr while staying plugin-friendly.
It is organised as a Python monorepo with a FastAPI core, a metadata proxy, and a Vite-based web UI.

## Quick start

```bash
git clone https://github.com/phelia-plugins/phelia.git
cd phelia
make up
```

The default `docker compose` stack exposes the API on http://localhost:8000 and the web UI on http://localhost:5173.
Environment overrides stay under `deploy/.env`; compose manifests live in `infrastructure/compose/`.

## Local development

- Install Python 3.10+ and Node 18+
- Use `make up` / `make down` to manage the stack (see `makefile` for helpers)
- Run smoke checks locally with `./scripts/dev_smoke.sh`

## Documentation

- [Architecture](docs/architecture.md)
- [Workflow](docs/workflow.md)
- [Cleanup inventory](docs/cleanup-inventory.md)
- Additional service-specific notes live in `docs/`
