from celery import Celery
from app.core.config import settings
from app.db.session import session_scope
from app.db.models import Download
from app.services.bt.qbittorrent import QbClient
import asyncio

celery_app = Celery(
    "music_autodl",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

async def _update_status(download_id: int):
    qb = QbClient(settings.QB_URL, settings.QB_USER, settings.QB_PASS)
    # fetch torrent hash from DB
    with session_scope() as db:
        dl = db.get(Download, download_id)
        if not dl or not dl.client_torrent_id:
            return
        torrent_hash = dl.client_torrent_id

    info = await qb.info_by_hash(torrent_hash)
    if not info:
        return

    with session_scope() as db:
        dl = db.get(Download, download_id)
        if not dl:
            return
        dl.progress = float(info.get('progress', 0.0))
        dl.status = info.get('state', 'downloading')
        dl.rate_down = int(info.get('dlspeed', 0))
        dl.rate_up = int(info.get('upspeed', 0))
        eta = info.get('eta')
        dl.eta_sec = int(eta) if eta not in (None, -1) else None

@celery_app.task
def enqueue_magnet(download_id: int, magnet: str, save_path: str | None = None):
    async def _run():
        qb = QbClient(settings.QB_URL, settings.QB_USER, settings.QB_PASS)
        torrent_hash = await qb.add_magnet(magnet, save_path)
        if torrent_hash:
            with session_scope() as db:
                dl = db.get(Download, download_id)
                if dl:
                    dl.client_torrent_id = torrent_hash
        # initial status write
        await _update_status(download_id)
    asyncio.run(_run())

@celery_app.task
def poll_status(download_id: int):
    asyncio.run(_update_status(download_id))
