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

### qBittorrent Compose wiring

```yaml
# docker-compose.yml (excerpt – for reference only)
services:
  qbittorrent:
    image: linuxserver/qbittorrent:latest
    ports:
      - "8080:8080"
    environment:
      - WEBUI_PORT=8080
      # Set initial credentials via the container image or config file
    volumes:
      - qb_config:/config
  api:
    build: .
    environment:
      - QBIT_URL=http://qbittorrent:8080
      - QBIT_USERNAME=admin
      - QBIT_PASSWORD=adminadmin
      - ADMIN_EMAIL=dev@example.com
      - ADMIN_PASSWORD=dev
    depends_on:
      - qbittorrent
```

Ensure the API talks to qBittorrent via the Docker service name (`http://qbittorrent:8080`) and that the supplied credentials match the qBittorrent configuration. When deploying behind a reverse proxy or Cloudflare, add `WebUI\\HostHeaderValidation=false` to `qBittorrent.conf` if the login probe is blocked.

## Local development

- Install Python 3.10+ and Node 18+
- Use `make up` / `make down` to manage the stack (see `makefile` for helpers)
- Run smoke checks locally with `./scripts/dev_smoke.sh`

## Documentation

- [Architecture](docs/architecture.md)
- [Workflow](docs/workflow.md)
- [Cleanup inventory](docs/cleanup-inventory.md)
- Additional service-specific notes live in `docs/`
