from __future__ import annotations

import asyncio
import inspect
import logging
import shutil
from pathlib import Path
from typing import List, Optional
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from celery import Celery
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.runtime_service_settings import runtime_service_settings
from app.db.models import Download
from app.db.session import SessionLocal
from app.services.broadcast import broadcast_download
from app.services.bt.qbittorrent import QbClient, QbittorrentLoginError


celery_app = Celery(
    "phelia",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

_POLL_SECONDS = 3.0
_FINAL_STATES = {"uploading", "stalledup", "pausedup", "forcedup"}

celery_app.conf.beat_schedule = {
    "poll-downloads": {
        "task": "app.services.jobs.tasks.poll_status",
        "schedule": _POLL_SECONDS,
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


def _mark_download_error(db: Session, dl: Download, code: str | None = None) -> None:
    dl.status = f"error:{code}" if code else "error"
    db.commit()
    broadcast_download(dl)


def _db() -> Session:
    return SessionLocal()


async def _maybe_await(result):
    if inspect.isawaitable(result):
        return await result
    return result


def _safe_tag(download_id: int) -> str:
    return f"phelia-{download_id}"


def _extract_info_hash(magnet: str | None) -> str | None:
    if not magnet:
        return None
    try:
        parsed = urlparse(magnet)
        if parsed.scheme != "magnet":
            return None
        xt_values = parse_qs(parsed.query).get("xt", [])
        for value in xt_values:
            decoded = unquote(value)
            if decoded.lower().startswith("urn:btih:"):
                return decoded.split(":")[-1].lower()
    except Exception:
        return None
    return None


def _torrent_matches_download(torrent: dict, d: Download) -> bool:
    tags_raw = str(torrent.get("tags") or "")
    tags = {tag.strip() for tag in tags_raw.split(",") if tag.strip()}
    if _safe_tag(d.id) in tags:
        return True
    if d.hash and (torrent.get("hash") or "").lower() == d.hash.lower():
        return True
    return False


def _pick_candidate(stats: List[dict], d: Download) -> Optional[dict]:
    for t in stats:
        if _torrent_matches_download(t, d):
            return t
    if d.name:
        for t in stats:
            if (t.get("name") or "").strip() == d.name.strip() and (t.get("save_path") or "") == d.save_path:
                return t
    return None


def _safe_list_torrents(qb: QbClient) -> List[dict]:
    try:
        res = qb.list_torrents()
        if inspect.isawaitable(res):
            return asyncio.run(res)
        return res
    except Exception as e:
        logger.warning("Failed to list torrents: %s", e)
        return []


async def _add_magnet_with_optional_tags(qb: QbClient, magnet: str, save_path: str, tag: str) -> None:
    try:
        await _maybe_await(qb.add_magnet(magnet, save_path=save_path, tags=tag))
    except TypeError:
        await _maybe_await(qb.add_magnet(magnet, save_path=save_path))


async def _add_file_with_optional_tags(qb: QbClient, torrent: bytes, save_path: str, tag: str) -> None:
    try:
        await _maybe_await(qb.add_torrent_file(torrent, save_path=save_path, tags=tag))
    except TypeError:
        await _maybe_await(qb.add_torrent_file(torrent, save_path=save_path))


def _safe_destination(base_dir: Path, item_name: str) -> Path:
    candidate = base_dir / item_name
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    idx = 1
    while True:
        deduped = candidate.with_name(f"{stem}-{idx}{suffix}")
        if not deduped.exists():
            return deduped
        idx += 1


def _cleanup_empty_dirs(start: Path, stop_at: Path) -> None:
    current = start
    while current != stop_at and stop_at in current.parents:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def _finalize_completed_download(db: Session, d: Download, torrent: dict) -> bool:
    content_path_raw = torrent.get("content_path") or ""
    name = str(torrent.get("name") or d.name or "").strip()
    if not content_path_raw or not name:
        logger.warning("Cannot finalize download %s: missing content path or name", d.id)
        return False

    source_path = Path(str(content_path_raw))
    final_root = Path(settings.DOWNLOAD_FINAL_DIR)
    final_root.mkdir(parents=True, exist_ok=True)
    destination = _safe_destination(final_root, source_path.name)

    d.status = "finalizing"
    db.commit()
    broadcast_download(d)

    moved = False
    try:
        if source_path.exists():
            shutil.move(str(source_path), str(destination))
            moved = True
        elif destination.exists():
            moved = True
        else:
            raise FileNotFoundError(f"Source path not found: {source_path}")

        d.save_path = str(destination.parent)
        d.name = destination.name
        d.progress = 1.0
        d.eta = 0
        d.dlspeed = 0
        d.upspeed = 0
        d.status = "completed"
        db.commit()
        broadcast_download(d)

        _cleanup_empty_dirs(source_path.parent, Path(settings.DOWNLOAD_STAGING_DIR))
        return True
    except Exception as exc:
        logger.exception("Failed to finalize download %s: %s", d.id, exc)
        d.status = "error:finalize"
        db.commit()
        broadcast_download(d)
        if moved and not destination.exists():
            logger.error("Finalization rollback required for download %s", d.id)
        return False


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

        parsed_hash = _extract_info_hash(dl.magnet or magnet)
        if parsed_hash:
            dl.hash = parsed_hash

        dl.status = "submitted"
        db.commit()
        broadcast_download(dl)

        if url and not dl.magnet and url.startswith("magnet:"):
            dl.magnet = url
            parsed_hash = _extract_info_hash(url)
            if parsed_hash:
                dl.hash = parsed_hash
            db.commit()
            broadcast_download(dl)
            url = None

        async def _run() -> List[dict]:
            qb = _qb()
            try:
                await _maybe_await(qb.login())
                content = b""
                if url and not dl.magnet:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(url, follow_redirects=False)
                        if resp.is_redirect:
                            loc = resp.headers.get("Location", "")
                            if loc.startswith("magnet:"):
                                dl.magnet = loc
                                parsed_hash = _extract_info_hash(loc)
                                if parsed_hash:
                                    dl.hash = parsed_hash
                                db.commit()
                                broadcast_download(dl)
                            else:
                                scheme = urlparse(loc).scheme if loc else ""
                                if scheme and scheme not in ("http", "https"):
                                    logger.warning(
                                        "Download %s redirect with unexpected scheme: %s",
                                        download_id,
                                        loc,
                                    )
                                    raise httpx.UnsupportedProtocol(loc)
                                resp = await client.get(loc or url, follow_redirects=True)
                                resp.raise_for_status()
                                content = resp.content
                        else:
                            resp.raise_for_status()
                            content = resp.content

                submit_dir = dl.save_path or settings.DOWNLOAD_STAGING_DIR
                if dl.magnet:
                    await _add_magnet_with_optional_tags(
                        qb, dl.magnet, save_path=submit_dir, tag=_safe_tag(dl.id)
                    )
                else:
                    await _add_file_with_optional_tags(
                        qb, content, save_path=submit_dir, tag=_safe_tag(dl.id)
                    )
                return await _maybe_await(qb.list_torrents())
            finally:
                close = getattr(qb, "close", None)
                if close:
                    await _maybe_await(close())

        try:
            stats = asyncio.run(_run())
        except QbittorrentLoginError as exc:
            logger.warning("qBittorrent auth error for %s: %s", download_id, exc)
            _mark_download_error(db, dl, exc.code)
            return False
        except Exception as exc:
            logger.exception("Failed to enqueue download for %s: %s", download_id, exc)
            _mark_download_error(db, dl)
            return False

        dl.status = "queued"
        db.commit()
        broadcast_download(dl)

        candidate = _pick_candidate(stats or [], dl)
        if candidate:
            cand_hash = candidate.get("hash")
            if cand_hash:
                dl.hash = cand_hash
            dl.name = candidate.get("name") or dl.name
            dl.status = candidate.get("state") or dl.status
            db.commit()
            broadcast_download(dl)
        return True
    finally:
        db.close()


@celery_app.task(name="app.services.jobs.tasks.poll_status")
def poll_status() -> int:
    db = _db()
    try:
        active: List[Download] = (
            db.query(Download)
            .filter(
                Download.status.in_(
                    (
                        "queued",
                        "submitted",
                        "downloading",
                        "stalled",
                        "checking",
                        "metaDL",
                        "allocating",
                        "moving",
                        "uploading",
                        "stalledUP",
                        "pausedUP",
                        "forcedUP",
                    )
                )
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
        except httpx.HTTPError as exc:
            logger.warning("HTTP error talking to qBittorrent: %s", exc)
            return 0
        except Exception as exc:
            logger.warning("Error talking to qBittorrent during polling: %s", exc)
            return 0

        changed = 0
        removed: list[Download] = []
        for d in active:
            t = _pick_candidate(stats, d)
            if not t:
                removed.append(d)
                continue

            t_hash = t.get("hash")
            if t_hash:
                d.hash = t_hash
            d.progress = float(t.get("progress") or 0.0)
            d.dlspeed = int(t.get("dlspeed") or 0)
            d.upspeed = int(t.get("upspeed") or 0)
            d.eta = int(t.get("eta") or 0)
            d.name = t.get("name") or d.name
            d.status = t.get("state") or d.status
            db.commit()
            broadcast_download(d)
            changed += 1

            if str(t.get("state") or "").lower() in _FINAL_STATES and d.status != "completed":
                finalized = _finalize_completed_download(db, d, t)
                if finalized and d.hash:
                    async def _delete() -> None:
                        qb = _qb()
                        try:
                            await _maybe_await(qb.login())
                            await _maybe_await(qb.delete_torrent(d.hash or "", delete_files=False))
                        finally:
                            close = getattr(qb, "close", None)
                            if close:
                                await _maybe_await(close())

                    try:
                        asyncio.run(_delete())
                    except Exception as exc:
                        logger.warning("Failed to remove finalized torrent %s from qBittorrent: %s", d.id, exc)

        if removed:
            for d in removed:
                logger.info("Pruning missing download %s", d.id)
                db.delete(d)
                changed += 1
            db.commit()
        return changed
    finally:
        db.close()


__all__ = ["celery_app", "enqueue_download", "poll_status"]
