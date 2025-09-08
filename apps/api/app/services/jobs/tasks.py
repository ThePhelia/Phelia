from __future__ import annotations
from typing import List, Optional

from celery import Celery
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.download import Download
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
        dl = db.query(Download).get(download_id)
        if not dl:
            return False
        if magnet and not dl.magnet:
            dl.magnet = magnet
        if save_path and not dl.save_path:
            dl.save_path = save_path
        if not dl.magnet:
            return False

        qb = _qb(); qb.login()
        qb.add_magnet(dl.magnet, save_path=dl.save_path or settings.DEFAULT_SAVE_DIR)
        dl.status = "queued"
        db.commit()

        stats = _safe_list_torrents(qb)
        if stats:
            cand = _pick_candidate(stats, dl)
            if cand:
                dl.name = cand.get("name") or dl.name
                dl.status = cand.get("state") or dl.status
                db.commit()
        return True
    finally:
        db.close()


@celery_app.task(name="app.services.jobs.tasks.poll_status")
def poll_status() -> int:
    db = _db()
    updated = 0
    try:
        active: List[Download] = (
            db.query(Download)
              .filter(Download.status.in_(("queued","downloading","stalled","checking")))
              .all()
        )
        if not active:
            return 0

        qb = _qb(); qb.login()
        stats = _safe_list_torrents(qb)
        if not stats:
            return 0

        for d in active:
            t = _pick_candidate(stats, d)
            if not t:
                continue
            d.progress = t.get("progress") or d.progress
            d.dlspeed = t.get("dlspeed") or d.dlspeed
            d.upspeed = t.get("upspeed") or d.upspeed
            d.status = t.get("state") or d.status
            d.eta = t.get("eta") or d.eta
            if not d.name and t.get("name"):
                d.name = t.get("name")
            updated += 1

        if updated:
            db.commit()
        return updated
    finally:
        db.close()


def _safe_list_torrents(qb: QbClient) -> List[dict]:
    try:
        return qb.list_torrents()
    except Exception:
        return []


def _pick_candidate(stats: List[dict], d: Download) -> Optional[dict]:
    if d.name:
        for t in stats:
            if (t.get("name") or "").strip() == d.name.strip():
                return t
    if d.save_path:
        cands = [t for t in stats if (t.get("save_path") or "") == d.save_path]
        if len(cands) == 1:
            return cands[0]
        if cands:
            return cands[0]
    return None

