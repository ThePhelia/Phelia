from __future__ import annotations
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import asyncio
import logging
import redis.asyncio as redis
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.runtime_service_settings import runtime_service_settings
from app.db.init_db import init_db
from app.db.session import session_scope
from app.routers import health, auth, downloads
from app.routes import discovery as discovery_routes
from phelia.routers import discovery as discovery_router
from app.api.v1.endpoints import discover as discover_endpoints
from app.api.v1.endpoints import meta as meta_endpoints
from app.api.v1.endpoints import search as metadata_search
from app.api.v1.endpoints import capabilities as capabilities_endpoints
from app.api.v1.endpoints import library as library_endpoints
from app.api.v1.endpoints import details as details_endpoints
from app.api.v1.endpoints import settings as settings_endpoints
from app.services.qbittorrent.health import qb_login_ok
from app.services.search.jackett.provider import JackettProvider
from app.services.search.registry import search_registry

logger = logging.getLogger(__name__)


def load_provider_credentials(_db) -> None:
    """Placeholder hook to preload provider credentials at startup."""
    return None


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
app.include_router(metadata_search.router, prefix="/api/v1")
app.include_router(meta_endpoints.router, prefix="/api/v1")
app.include_router(discover_endpoints.router, prefix="/api/v1")
app.include_router(discovery_routes.router)
app.include_router(discovery_router.router, prefix="/discovery", tags=["discovery"])
app.include_router(capabilities_endpoints.router, prefix="/api/v1")
app.include_router(library_endpoints.router, prefix="/api/v1")
app.include_router(details_endpoints.router, prefix="/api/v1")
app.include_router(settings_endpoints.router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    try:
        init_db()
    except IntegrityError:
        logger.warning("Database already seeded; skipping admin bootstrap")
    except Exception:
        logger.exception("Error initializing database")

    try:
        with session_scope() as db:
            load_provider_credentials(db)
    except Exception:
        logger.exception("Error loading provider credentials")

    try:
        jackett_settings = runtime_service_settings.jackett_settings()
        search_registry.register(
            JackettProvider(jackett_settings, logger=logging.getLogger("phelia.jackett"))
        )
    except Exception:
        logger.exception("Error initializing Jackett search provider")

    try:
        login_ok = await asyncio.to_thread(qb_login_ok)
        if login_ok is False:
            logger.error("Error checking qBittorrent connectivity")
        elif login_ok is None:
            logger.info("qBittorrent health-check skipped during startup")
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
