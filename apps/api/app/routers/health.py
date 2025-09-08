from fastapi import APIRouter, HTTPException
from app.core.config import settings
from app.services.bt.qbittorrent import QbClient
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
async def health():
    try:
        async with QbClient(settings.QB_URL, settings.QB_USER, settings.QB_PASS) as qb:
            await qb.login()
            items = await qb.list_torrents()
    except Exception:
        logger.exception("Failed to reach qBittorrent")
        raise HTTPException(status_code=502, detail="qBittorrent unreachable")
    return {"ok": True, "details": {"qbittorrent": {"ok": True, "count": len(items)}}}
