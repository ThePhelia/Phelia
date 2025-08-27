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

# Simple status poller by torrent list (MVP). In production, track hash/id explicitly.
async def _update_status(download_id: int):
    qb = QbClient(settings.QB_URL, settings.QB_USER, settings.QB_PASS)
    await qb.login()
    items = await qb.list_torrents()
    # naive: take the last added torrent as the one we just enqueued if id has no client_torrent_id
    with session_scope() as db:
        dl = db.get(Download, download_id)
        if not dl:
            return
        if items:
            # Find best match by save_path (if unique) else pick most recent
            item = sorted(items, key=lambda x: x.get('added_on', 0), reverse=True)[0]
            dl.client_torrent_id = item.get('hash')
            dl.progress = float(item.get('progress', 0.0))
            dl.status = item.get('state', 'downloading')
            dl.rate_down = int(item.get('dlspeed', 0))
            dl.rate_up = int(item.get('upspeed', 0))
            dl.eta_sec = int(item.get('eta', -1)) if item.get('eta') not in (None, -1) else None

@celery_app.task
def enqueue_magnet(download_id: int, magnet: str, save_path: str | None = None):
    async def _run():
        qb = QbClient(settings.QB_URL, settings.QB_USER, settings.QB_PASS)
        await qb.add_magnet(magnet, save_path)
        # initial status write
        await _update_status(download_id)
    asyncio.run(_run())

@celery_app.task
def poll_status(download_id: int):
    asyncio.run(_update_status(download_id))
