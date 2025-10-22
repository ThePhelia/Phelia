# Architecture

Phelia ships as a set of loosely coupled services that communicate over HTTP and message queues.
The high-level flow is:

1. **Frontend (Vite/React)** – Presents discovery, library, and automation controls. Talks only to the core API.
2. **Core API (FastAPI)** – Hosts user flows, plugin integration, job scheduling, and dispatch to background workers.
3. **Metadata services** – Movie/TV/music discovery live inside the core today but are earmarked to graduate into their own `apps/metadata_*` services.
4. **Metadata Proxy** – Centralises outbound calls to TMDB, Fanart, MusicBrainz, Last.fm, etc. Applies caching and rate limiting.
5. **Plugin Host** – Future service for executing sandboxed plugins and exposing their routes to the core.
6. **Proxy Keys** – Planned thin facade that holds external API credentials. All outbound provider calls will go through this service once implemented.

```text
Frontend → Core API → Metadata services → Plugin Host → Proxy Keys → External providers
```

## Service boundaries

### Core API (`apps/api` → future `apps/core`)
- Exposes REST and websocket endpoints.
- Owns the database, authentication, downloads orchestration, and plugin lifecycle.
- Dispatches background jobs to Celery workers (`worker`, `beat`).

### Metadata services (`apps/metadata_*` placeholders)
- Will encapsulate the per-domain metadata pipelines (movies, TV, music).
- Continue to source data via the metadata proxy and return aggregated payloads to the core API.

### Metadata Proxy (`services/metadata-proxy`)
- FastAPI app that fans out to TMDB, Fanart, Last.fm, and MusicBrainz.
- Provides `/health` plus provider-specific routes.
- Caches responses and enforces polite rate limits.

### Plugin Host (`apps/plugin_host` placeholder)
- Targeted to execute plugin bundles and expose their configuration schemas.
- Communicates with the core API over RPC/HTTP and event queues.

### Proxy Keys (`apps/proxy_keys` placeholder)
- Contract: external provider APIs **must** be accessed via this service; never embed raw keys in code.
- Will return signed/temporary credentials to the metadata proxy and plugin host.

## North Star (next month)

- Restore a minimal music metadata MVP powered by the proxy.
- Ship the plugin host skeleton and begin loading safe plugins out-of-process.
- Publish the first Jackett bridge plugin as an example.
- Design and agree on the proxy-keys API contract.
