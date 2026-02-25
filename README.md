# Phelia

Phelia is a modular media automation stack that mirrors the capabilities of Sonarr/Radarr.
It is organised as a Python monorepo with a FastAPI core, a FastAPI metadata backend, and a Vite-based web UI.

## Quick start

```bash
git clone https://github.com/phelia/phelia.git
cd phelia
make up
```

The default `docker compose` stack exposes the API on http://localhost:8000 and the web UI on http://localhost:5173.
Environment overrides stay under `deploy/.env`; compose manifests live in `infrastructure/compose/`.

### qBittorrent + secrets persistence

The compose stack now persists all integration settings and qBittorrent config via named volumes:

- `qbittorrent_config` → qBittorrent `/config` (WebUI credentials and app settings)
- `prowlarr_config` → Prowlarr `/config` (mounted read-only to API/worker for API key discovery)
- `app_data` → shared app secrets store at `/data/secrets.json.enc` (mounted into API, worker, beat)

`docker compose down` keeps volumes. `docker compose down -v` **deletes all named volumes** and wipes persisted settings/keys.

Prowlarr API key entry is optional in normal compose setups: when `prowlarr_config` is mounted, the backend auto-discovers the API key from `config.xml` and stores it in the shared encrypted secrets store.

## Credential reset/rotation

qBittorrent WebUI credentials are bootstrapped on first startup only. The bootstrap script writes `QB_USER` + `QB_PASS` into `/config/qBittorrent/qBittorrent.conf` (inside the persisted `qbittorrent_config` volume) when that config does not exist yet.

Because `qbittorrent_config` is persisted, changing `QB_USER` / `QB_PASS` in env files later does **not** change qBittorrent credentials by default. Subsequent starts detect existing config and skip credential writes.

Use one of these deterministic reset paths:

1. **Forced rotation (recommended when you want to keep other qB settings):**
   - Set `QB_BOOTSTRAP_FORCE=true` for a single startup.
   - Start/restart qBittorrent; bootstrap will rewrite WebUI credentials from current env values.
   - Set it back to `false` (default) afterward.
2. **Delete volume (full reset):**
   - Run `docker compose down -v` (or remove only `qbittorrent_config`).
   - Next startup behaves like first-run bootstrap and initializes credentials from env.

Choose forced rotation when only credential updates are needed. Choose volume deletion when you intentionally want a full qBittorrent configuration reset.


## Local development

- Install Python 3.10+ and Node 18+
- Use `make up` / `make down` to manage the stack (see `makefile` for helpers)
- Run smoke checks locally with `./scripts/dev_smoke.sh`

## Documentation

- [Architecture](docs/architecture.md)
- [Workflow](docs/workflow.md)
- [Cleanup inventory](docs/cleanup-inventory.md)
- Additional service-specific notes live in `docs/`
