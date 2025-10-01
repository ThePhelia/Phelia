"""Capabilities endpoint exposing service status for the web UI."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.runtime_settings import runtime_settings
from app.schemas.ui import CapabilitiesResponse
from app.services.bt.qbittorrent import QbClient
from app.services.search.registry import search_registry


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
        "torrent_search": search_registry.is_configured(),
        "tmdb": runtime_settings.tmdb_enabled,
        "omdb": runtime_settings.omdb_enabled,
        "discogs": runtime_settings.discogs_enabled,
        "lastfm": runtime_settings.lastfm_enabled,
    }

    version = getattr(request.app, "version", None) or "unknown"

    return CapabilitiesResponse(
        services=services,
        version=version,
        links=None,
    )
