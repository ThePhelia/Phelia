from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import logging

from app.core.config import settings
from app.db.init_db import init_db
from app.routers import health, auth, downloads, search, trackers
from app.services.search.jackett_bootstrap import ensure_jackett_tracker

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
def startup_event():
    try:
        init_db()
    except Exception as e:
        logger.exception("Error initializing database")
    try:
        ensure_jackett_tracker()
    except Exception as e:
        logger.exception("Error ensuring Jackett tracker")

