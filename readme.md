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


