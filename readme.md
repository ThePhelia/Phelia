# Music AutoDL — First Commit

MVP: Postgres + Redis + qBittorrent + FastAPI + Celery. Add a magnet, watch status.

## 0) Prereqs
- Docker + Docker Compose
- Free TCP/UDP ports (override via env if needed)

## 1) Configure env
```bash
cp deploy/env/api.example.env deploy/env/api.env
# edit deploy/env/api.env as needed
# Optionally override ports via compose env:
# export API_PORT=8010 QB_WEB_PORT=8181 BT_PORT_TCP=50413 BT_PORT_UDP=50413
