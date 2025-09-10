from __future__ import annotations
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import logging
import redis.asyncio as redis

from app.core.config import settings
from app.db.init_db import init_db
from app.routers import health, auth, downloads, search, trackers
from app.services.search.jackett_bootstrap import ensure_jackett_tracker
from app.services.bt.qbittorrent import health_check as qb_health_check

logger = logging.getLogger(__name__)

app = FastAPI(title="Phelia", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(downloads.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(trackers.router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    try:
        init_db()
    except Exception as e:
        logger.exception("Error initializing database")
    try:
        ensure_jackett_tracker()
    except Exception as e:
        logger.exception("Error ensuring Jackett tracker")
    try:
        await qb_health_check()
    except Exception:
        logger.exception("Error checking qBittorrent connectivity")


@app.websocket("/ws/downloads/{download_id}")
async def download_ws(websocket: WebSocket, download_id: int):
    await websocket.accept()
    r = redis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    channel = f"downloads:{download_id}"
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if isinstance(data, bytes):
                data = data.decode()
            try:
                await websocket.send_text(data)
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await r.close()

