"""Capabilities endpoint exposing service status for the web UI."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.core.config import settings
from app.schemas.ui import CapabilitiesResponse
from app.services.bt.qbittorrent import QbClient


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


async def _check_qbittorrent() -> bool:
    client = QbClient(settings.QB_URL, settings.QB_USER, settings.QB_PASS, timeout=5.0)
    try:
        async with client:
            await client.login()
            await client.list_torrents()
        return True
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("Failed to query qBittorrent health")
        return False


@router.get("", response_model=CapabilitiesResponse)
async def read_capabilities(request: Request) -> CapabilitiesResponse:
    qb_ok = await _check_qbittorrent()

    services = {
        "qbittorrent": qb_ok,
        "jackett": bool(settings.JACKETT_API_KEY),
        "tmdb": bool(settings.TMDB_API_KEY),
        "omdb": bool(settings.OMDB_API_KEY),
        "discogs": bool(settings.DISCOGS_TOKEN),
        "lastfm": bool(settings.LASTFM_API_KEY),
    }

    version = getattr(request.app, "version", None) or "unknown"

    return CapabilitiesResponse(
        services=services,
        version=version,
        links={"jackett": settings.jackett_public_url},
    )
