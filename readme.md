# Phelia

Phelia is a self-hosted media automation platform with a **modular plugin architecture**.  
It combines ideas from Sonarr, Radarr, Jackett, and music discovery tools, but is built to be **extensible, self-contained, and community-driven**.  

Phelia is not just another PVR — it is a framework where every feature (indexers, metadata providers, discovery panels, even UI settings) can be extended via plugins.

---

## Core Concepts

- **Plugin Architecture**  
  Phelia supports `.phex` plugin packages.  
  Plugins can:
  - Add discovery sources (movies, TV, music, etc.)
  - Integrate external APIs (TMDB, Discogs, Last.fm, …)
  - Provide torrent indexers (Jackett-style) or alternative providers
  - Extend the UI with new settings panels and actions  

- **Unified Media Discovery**  
  Out of the box, Phelia provides discovery for movies, TV shows, and music.  
  Search results open rich panels with metadata, and a single click can trigger indexing/downloading via connected providers.

- **Automation Layer**  
  Like a PVR, Phelia can watch for new content, search via configured providers, and send it to your download client (qBittorrent or others).  

- **Extensible Store**  
  A public [plugin index](https://phelia-plugins.github.io) lists available plugins.  
  Users can install plugins directly from the UI.  

---

## 🏗 Architecture

Phelia is built as a distributed service with separate components:

- **API** – FastAPI backend, database access, plugin loading  
- **Web** – React + Tailwind UI with dynamic plugin settings pages  
- **Worker** – Celery workers for background tasks (indexing, API calls, downloads)  
- **Beat** – Celery scheduler for periodic jobs  
- **DB** – PostgreSQL (media library, users, plugin state)  
- **Redis** – task queue backend  
- **Download Client** – qBittorrent supported by default  

All services are orchestrated via `docker compose`.

---

## Getting Started

### Prerequisites
- Docker & Docker Compose
- At least 2GB RAM recommended for smooth operation

### Installation

```bash
git clone https://github .com/phelia-plugins/phelia.git
cd phelia
make up
```

### After Startup
- WebUI: http://localhost:5173/
- Default login: created on first launch

## Plugins

Plugins are distributed as .phex archives.
They can be installed manually or from the built-in store.

### Installing manually

Download .phex file

Upload via Plugins → Install in the UI

### Installing from store

Open Plugins → Store

Browse available plugins

One-click install

## ⚠️ Disclaimer

Phelia does not come pre-configured with trackers or indexers.
Users are responsible for how they use plugins and providers.
The project itself does not endorse piracy.
