# Phelia

AIO Self-Hosted Torrent Parser and Client for home media-servers

## WebSocket Updates

The API exposes a WebSocket endpoint that streams download progress in
real time. Connect to `/ws/downloads/{id}` where `id` is the download
identifier returned by the REST API:

```
const ws = new WebSocket("ws://localhost:8000/ws/downloads/1");
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

Messages are JSON objects containing the current fields of the download
such as `progress`, `status`, `dlspeed` and `upspeed`.

## First run

The API connects to the qBittorrent Web UI using credentials defined in
`deploy/env/api.env`.

1. Start the stack with `docker compose up -d` from the `deploy/`
   directory.
2. Visit `http://localhost:8080` and log in to the qBittorrent Web UI
   using the default credentials `admin` / `adminadmin`.
3. If you change the password, update `QB_USER` and `QB_PASS` in
   `deploy/env/api.env` to match. These values **must** remain in sync
   or the API will fail to authenticate with qBittorrent at
   `http://qbittorrent:8080`.


