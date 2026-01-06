from __future__ import annotations

import asyncio
import inspect
import logging
from typing import List, Optional
from urllib.parse import urlparse

import httpx
from celery import Celery
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.runtime_service_settings import runtime_service_settings
from app.db.session import SessionLocal
from app.db.models import Download
from app.services.bt.qbittorrent import QbClient
from app.services.broadcast import broadcast_download


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
logger = logging.getLogger(__name__)


def _qb() -> QbClient:
    qb = runtime_service_settings.qbittorrent_snapshot()
    return QbClient(
        base_url=qb.url,
        username=qb.username,
        password=qb.password,
    )


def _db() -> Session:
    return SessionLocal()


async def _maybe_await(result):
    if inspect.isawaitable(result):
        return await result
    return result


@celery_app.task(name="app.services.jobs.tasks.enqueue_download")
def enqueue_download(
    download_id: int,
    magnet: Optional[str] = None,
    url: Optional[str] = None,
    save_path: Optional[str] = None,
) -> bool:
    db = _db()
    try:
        dl = db.get(Download, download_id)
        if not dl:
            logger.warning("Download %s not found", download_id)
            return False
        if magnet and not dl.magnet:
            dl.magnet = magnet
        if save_path and not dl.save_path:
            dl.save_path = save_path
        if not dl.magnet and not url:
            logger.warning("Download %s missing magnet or url", download_id)
            return False
        else:
            if url and not dl.magnet:
                if url.startswith("magnet:"):
                    dl.magnet = url
                    url = None
                else:
                    scheme = urlparse(url).scheme
                    if scheme and scheme not in ("http", "https"):
                        logger.error(
                            "Unrecognized URL scheme for download %s: %s",
                            download_id,
                            url,
                        )
                        return False

            async def _run() -> List[dict]:
                qb = _qb()
                try:
                    await _maybe_await(qb.login())
                    content = b""
                    if url and not dl.magnet:
                        try:
                            async with httpx.AsyncClient() as client:
                                resp = await client.get(url, follow_redirects=False)
                                if resp.is_redirect:
                                    loc = resp.headers.get("Location", "")
                                    if loc.startswith("magnet:"):
                                        dl.magnet = loc
                                        db.commit()
                                        content = b""
                                    else:
                                        if loc:
                                            scheme = urlparse(loc).scheme
                                        if scheme and scheme not in ("http", "https"):
                                            logger.warning(
                                                "Download %s redirect with unexpected scheme: %s",
                                                download_id,
                                                loc,
                                            )
                                            raise httpx.UnsupportedProtocol(loc)
                                        resp.raise_for_status()
                                        content = resp.content
                                else:
                                    resp.raise_for_status()
                                    content = resp.content
                        except httpx.HTTPError as e:
                            logger.error("Failed to fetch %s: %s", url, e)
                            dl.status = "error"
                            db.commit()
                            broadcast_download(dl)
                            raise
                    if dl.magnet:
                        await _maybe_await(
                            qb.add_magnet(
                                dl.magnet,
                                save_path=dl.save_path
                                or runtime_service_settings.download_snapshot().default_dir,
                            )
                        )
                    else:
                        await _maybe_await(
                            qb.add_torrent_file(
                                content,
                                save_path=dl.save_path
                                or runtime_service_settings.download_snapshot().default_dir,
                            )
                        )
                    return await _maybe_await(qb.list_torrents())
                except httpx.HTTPError as e:
                    logger.error(
                        "HTTP error talking to qBittorrent for %s: %s", download_id, e
                    )
                    dl.status = "error"
                    db.commit()
                    broadcast_download(dl)
                    raise
                finally:
                    close = getattr(qb, "close", None)
                    if close:
                        await _maybe_await(close())

            try:
                stats = asyncio.run(_run())
            except Exception as e:
                logger.exception(
                    "Failed to enqueue download for %s: %s", download_id, e
                )
                dl.status = "error"
                db.commit()
                broadcast_download(dl)
                return False

            dl.status = "queued"
            db.commit()
            broadcast_download(dl)

            if stats:
                cand = _pick_candidate(stats, dl)
                if cand:
                    dl.name = cand.get("name") or dl.name
                    dl.status = cand.get("state") or dl.status
                    cand_hash = cand.get("hash")
                    if cand_hash:
                        dl.hash = cand_hash
                    db.commit()
                    broadcast_download(dl)
            return True
    except Exception as e:
        logger.exception("Error in enqueue_download for %s: %s", download_id, e)
        dl = locals().get("dl")
        if dl:
            dl.status = "error"
            db.commit()
            broadcast_download(dl)
        return False
    finally:
        db.close()


@celery_app.task(name="app.services.jobs.tasks.poll_status")
def poll_status() -> int:
    db = _db()
    try:
        active: List[Download] = (
            db.query(Download)
            .filter(
                Download.status.in_(("queued", "downloading", "stalled", "checking"))
            )
            .all()
        )
        if not active:
            return 0

        async def _run() -> List[dict]:
            qb = _qb()
            try:
                await _maybe_await(qb.login())
                return await _maybe_await(qb.list_torrents())
            finally:
                close = getattr(qb, "close", None)
                if close:
                    await _maybe_await(close())

        try:
            stats = asyncio.run(_run())
        except httpx.HTTPError as e:
            logger.warning("HTTP error talking to qBittorrent: %s", e)
            return 0
        if not stats:
            return 0

        changed: List[Download] = []
        removed: List[Download] = []
        for d in active:
            t = _pick_candidate(stats, d)
            if not t:
                removed.append(d)
                continue
            t_hash = t.get("hash")
            if t_hash:
                d.hash = t_hash
            d.progress = t.get("progress") or d.progress
            d.dlspeed = t.get("dlspeed") or d.dlspeed
            d.upspeed = t.get("upspeed") or d.upspeed
            d.status = t.get("state") or d.status
            d.eta = t.get("eta") or d.eta
            if not d.name and t.get("name"):
                d.name = t.get("name")
            changed.append(d)

        if removed:
            for d in removed:
                logger.info("Pruning missing download %s", d.id)
                db.delete(d)

        if changed or removed:
            db.commit()
            for d in changed:
                broadcast_download(d)
        return len(changed) + len(removed)
    finally:
        db.close()


def _safe_list_torrents(qb: QbClient) -> List[dict]:
    try:
        res = qb.list_torrents()
        if inspect.isawaitable(res):
            return asyncio.run(res)
        return res
    except Exception as e:
        logger.warning("Failed to list torrents: %s", e)
        return []


def _pick_candidate(stats: List[dict], d: Download) -> Optional[dict]:
    if d.hash:
        h = d.hash.lower()
        for t in stats:
            if (t.get("hash") or "").lower() == h:
                return t
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
