from __future__ import annotations
from typing import List, Optional

from celery import Celery
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.db import models
from app.services.bt.qbittorrent import QbClient


celery_app = Celery(
    "phelia",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.beat_schedule = {
    "poll-downloads": {
        "task": "app.services.jobs.tasks.poll_status",
        "schedule": 15.0,
    }
}
celery_app.conf.timezone = "UTC"


def _qb() -> QbClient:
    return QbClient(
        base_url=settings.QB_URL,
        username=settings.QB_USER,
        password=settings.QB_PASS,
    )

def _db() -> Session:
    return SessionLocal()


@celery_app.task(name="app.services.jobs.tasks.enqueue_magnet")
def enqueue_magnet(download_id: int, magnet: Optional[str] = None, save_path: Optional[str] = None) -> bool:
    db = _db()
    try:
        dl = db.query(models.Download).get(download_id)
        if not dl:
            return False
        if magnet and not dl.magnet:
            dl.magnet = magnet
        if save_path and not dl.save_path:
            dl.save_path = save_path
        if not dl.magnet:
            return False
        qb = _qb(); qb.login()
        if dl.hash:
            return True
        _ = qb.add_magnet(dl.magnet, save_path=dl.save_path or settings.DEFAULT_SAVE_DIR)
        dl.status = "queued"
        db.commit()
        return True
    finally:
        db.close()


@celery_app.task(name="app.services.jobs.tasks.poll_status")
def poll_status() -> int:
    db = _db()
    updated = 0
    try:
        active: List[models.Download] = (
            db.query(models.Download)
              .filter(models.Download.status.in_(("queued","downloading","stalled","checking")))
              .all()
        )
        if not active:
            return 0
        qb = _qb(); qb.login()
        by_hash = {d.hash: d for d in active if d.hash}
        if by_hash:
            stats = qb.list_torrents()
            for s in stats:
                h = s.get("hash")
                if not h or h not in by_hash:
                    continue
                dl = by_hash[h]
                dl.progress = s.get("progress")
                dl.dlspeed = s.get("dlspeed")
                dl.upspeed = s.get("upspeed")
                dl.status = s.get("state")
                dl.eta = s.get("eta")
                updated += 1
            db.commit()
        return updated
    finally:
        db.close()

