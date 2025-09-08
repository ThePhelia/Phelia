from fastapi import APIRouter
from app.core.config import settings
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
        async with QbClient(settings.QB_URL, settings.QB_USER, settings.QB_PASS) as qb:
            await qb.login()
            items = await qb.list_torrents()
            qb_status.update({"count": len(items)})
    except Exception:
        logger.exception("Failed to reach qBittorrent")
        qb_status["ok"] = False
    return {"ok": True, "details": {"qbittorrent": qb_status}}
