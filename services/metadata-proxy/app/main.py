"""FastAPI application entrypoint for the metadata proxy."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .cache import close_cache, init_cache
from .clients.fanart import router as fanart_router
from .clients.lastfm import router as lastfm_router
from .clients.musicbrainz import router as musicbrainz_router
from .clients.tmdb import router as tmdb_router
from .config import get_settings
from .health import router as health_router
from .http import close_http_client

logger = logging.getLogger("metadata_proxy")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    await init_cache(settings)
    try:
        yield
    finally:
        await close_cache()
        await close_http_client()


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    app = FastAPI(title="Phelia Metadata Proxy", lifespan=lifespan)

    app.include_router(health_router, prefix="/health")
    app.include_router(tmdb_router, prefix="/tmdb")
    app.include_router(lastfm_router, prefix="/lastfm")
    app.include_router(musicbrainz_router, prefix="/mb")
    app.include_router(fanart_router, prefix="/fanart")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, factory=False)
