from fastapi import APIRouter
from app.core.config import settings
from app.services.bt.qbittorrent import QbClient
import asyncio

router = APIRouter()

@router.get("/health")
async def health():
    ok = True
    details = {}
    # qBittorrent
    try:
        qb = QbClient(settings.QB_URL, settings.QB_USER, settings.QB_PASS)
        await qb.login()
        items = await qb.list_torrents()
        details["qbittorrent"] = {"ok": True, "count": len(items)}
    except Exception as e:
        ok = False
        details["qbittorrent"] = {"ok": False, "error": str(e)}
    return {"ok": ok, "details": details}
