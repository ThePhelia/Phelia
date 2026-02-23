# Architecture

Phelia ships as a set of loosely coupled services that communicate over HTTP and message queues.
The high-level flow is:

1. **Frontend (Vite/React)** – Presents discovery, library, and automation controls. Talks only to the core API.
2. **Core API (FastAPI)** – Hosts user flows, search/discovery orchestration, metadata lookups, job scheduling, and dispatch to background workers.
3. **Metadata services** – Movie/TV/music discovery currently run inside the core API, with optional future extraction into domain services.

```text
Frontend → Core API → External providers (TMDb/OMDb/Last.fm/MusicBrainz/etc)
```

## Service boundaries

### Core API (`apps/api`)
- Exposes REST and websocket endpoints.
- Owns database access, downloads orchestration, and settings lifecycle.
- Stores integration keys in the server-side secrets store.
- Performs direct upstream metadata calls.

### Metadata services (`apps/metadata_*` placeholders)
- Future optional extraction for per-domain metadata pipelines (movies, TV, music).
- Any extracted services should still receive credentials from backend-managed secrets, never from the browser.

## Notes

- The web app is reverse proxied to the API (`/api/v1` → `api:8121`) and never calls TMDb/OMDb directly from the browser.
- TMDb/OMDb API keys are user-provided via settings and only persisted server-side.
