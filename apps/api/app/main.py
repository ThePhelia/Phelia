from __future__ import annotations
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import logging
import redis.asyncio as redis

from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import session_scope
from app.routers import health, auth, downloads, trackers
from app.api.v1.endpoints import discover as discover_endpoints
from app.api.v1.endpoints import meta as meta_endpoints
from app.api.v1.endpoints import search as metadata_search
from app.api.v1.endpoints import capabilities as capabilities_endpoints
from app.api.v1.endpoints import library as library_endpoints
from app.api.v1.endpoints import details as details_endpoints
from app.api.v1.endpoints import settings as settings_endpoints
from app.api.v1.endpoints import index as index_endpoints
from app.services.search.jackett_bootstrap import ensure_jackett_tracker
from app.services.bt.qbittorrent import health_check as qb_health_check
from app.services.settings import load_provider_credentials

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
app.include_router(trackers.router, prefix="/api/v1")
app.include_router(metadata_search.router, prefix="/api/v1")
app.include_router(meta_endpoints.public_router, prefix="/api/v1/meta")
app.include_router(discover_endpoints.router, prefix="/api/v1")
app.include_router(index_endpoints.router, prefix="/api/v1/index")
app.include_router(capabilities_endpoints.router, prefix="/api/v1")
app.include_router(library_endpoints.router, prefix="/api/v1")
app.include_router(details_endpoints.router, prefix="/api/v1")
app.include_router(settings_endpoints.router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    try:
        init_db()
    except Exception as e:
        logger.exception("Error initializing database")
    try:
        with session_scope() as db:
            load_provider_credentials(db)
    except Exception:
        logger.exception("Error loading provider credentials")
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

