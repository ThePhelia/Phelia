# Jackett Integrator

Jackett Integrator provisions a LinuxServer Jackett container for Torznab search
and forwards torrent selections to qBittorrent through Phelia's torrent client.

## Requirements

- Docker with `docker compose` available to the Phelia host
- Running qBittorrent instance at `http://qbittorrent:8080`
- Phelia backend ≥ `0.7.0`

## Installation

1. Build the plugin archive:

   ```bash
   python plugins/jackett_integrator/scripts/build_phex.py
   ```

   The command emits `plugins/jackett_integrator/dist/phelia.jackett-0.2.1.phex`.

2. Upload the `.phex` through the Phelia Market UI or POST it to
   `/api/v1/market/plugins/install/upload`.

3. Enable the plugin; the install hook boots Jackett, captures its API key, and
   registers the search provider.

## Configuration

The plugin registers a settings panel containing:

- `JACKETT_URL` (default `http://jackett:9117`)
- `JACKETT_API_KEY` (auto-populated on first enable)
- `QBITTORRENT_URL` (default `http://qbittorrent:8080`)
- `QBITTORRENT_USERNAME` / `QBITTORRENT_PASSWORD`
- Optional allowlist/blocklist, category filters, and minimum seeder threshold

Ensure qBittorrent credentials are valid before using the **Send to qBittorrent**
action from search results.

## Development

- Run tests:

  ```bash
  pytest plugins/jackett_integrator/tests
  ```

- Build archive to a custom location:

  ```bash
  python plugins/jackett_integrator/scripts/build_phex.py --output /tmp/phelia.jackett.phex
  ```
