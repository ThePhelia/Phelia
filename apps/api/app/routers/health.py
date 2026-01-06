from fastapi import APIRouter
from app.core.runtime_service_settings import runtime_service_settings
from app.services.bt.qbittorrent import QbClient
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


@router.get("/health")
async def health() -> dict:
    qb_status = {"ok": True}
    try:
        qb_settings = runtime_service_settings.qbittorrent_snapshot()
        async with QbClient(
            qb_settings.url, qb_settings.username, qb_settings.password
        ) as qb:
            await qb.login()
            items = await qb.list_torrents()
            qb_status.update({"count": len(items)})
    except Exception:
        logger.exception("Failed to reach qBittorrent")
        qb_status["ok"] = False
    return {"ok": True, "details": {"qbittorrent": qb_status}}
