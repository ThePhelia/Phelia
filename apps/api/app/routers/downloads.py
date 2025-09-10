from __future__ import annotations
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
import logging
import time
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models
from app.core.config import settings
from app.services.jobs.tasks import celery_app
from app.services.bt.qbittorrent import QbClient


router = APIRouter(prefix="/downloads", tags=["downloads"])
logger = logging.getLogger(__name__)


class DownloadCreate(BaseModel):
    magnet: Optional[str] = Field(default=None, min_length=10)
    url: Optional[str] = None
    savePath: Optional[str] = None

    @model_validator(mode="after")
    def _validate_source(self):
        if not (self.magnet or self.url):
            raise ValueError("Either magnet or url must be provided")
        return self


class DownloadOut(BaseModel):
    id: int
    name: Optional[str] = None
    magnet: Optional[str] = None
    hash: Optional[str] = None
    progress: Optional[float] = None
    dlspeed: Optional[int] = None
    upspeed: Optional[int] = None
    status: Optional[str] = None
    eta: Optional[int] = None
    save_path: Optional[str] = None

    class Config:
        from_attributes = True


def _qb() -> QbClient:
    return QbClient(settings.QB_URL, settings.QB_USER, settings.QB_PASS)


@router.get("", response_model=List[DownloadOut])
def list_downloads(db: Session = Depends(get_db)):
    q = db.query(models.Download).order_by(models.Download.id.desc()).all()
    return q


@router.post("", response_model=dict, status_code=201)
def create_download(body: DownloadCreate, db: Session = Depends(get_db)):
    save_path = body.savePath or settings.DEFAULT_SAVE_DIR
    dl = models.Download(magnet=body.magnet or "", save_path=save_path, status="queued")
    db.add(dl)
    db.commit()
    db.refresh(dl)
    logger.info(
        "Enqueuing download magnet=%s url=%s to %s", body.magnet, body.url, save_path
    )
    try:
        res = celery_app.send_task(
            "app.services.jobs.tasks.enqueue_download",
            args=[dl.id, body.magnet, body.url, save_path],
        )
        task_id = getattr(res, "id", "unknown")
        logger.info("Celery task %s dispatched for download %s", task_id, dl.id)
        if res.failed():
            logger.error(
                "Celery task %s failed for magnet %s url %s", task_id, body.magnet, body.url
            )
            dl.status = "error"
            db.commit()
            raise HTTPException(500, "Failed to enqueue download")

        deadline = time.time() + 2
        while time.time() < deadline:
            db.refresh(dl)
            if dl.status == "error":
                detail = "Failed to reach qBittorrent"
                logger.error(detail)
                raise HTTPException(status_code=502, detail=detail)
            time.sleep(0.1)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Failed to enqueue download magnet=%s url=%s to %s: %s",
            body.magnet,
            body.url,
            save_path,
            e,
        )
        dl.status = "error"
        db.commit()
        raise HTTPException(500, "Failed to enqueue download")
    return {"id": dl.id}


@router.post("/{download_id}/pause", status_code=204)
async def pause_download(download_id: int, db: Session = Depends(get_db)):
    dl = db.get(models.Download, download_id)
    if not dl:
        raise HTTPException(404, "Not found")
    if not dl.hash:
        raise HTTPException(409, "hash is not assigned yet")
    async with _qb() as qb:
        await qb.login()
        logger.info("Pausing torrent %s", dl.hash)
        await qb.pause_torrent(dl.hash)
        logger.info("Paused torrent %s", dl.hash)
    return JSONResponse(status_code=204, content={})


@router.post("/{download_id}/resume", status_code=204)
async def resume_download(download_id: int, db: Session = Depends(get_db)):
    dl = db.get(models.Download, download_id)
    if not dl:
        raise HTTPException(404, "Not found")
    if not dl.hash:
        raise HTTPException(409, "hash is not assigned yet")
    async with _qb() as qb:
        await qb.login()
        logger.info("Resuming torrent %s", dl.hash)
        await qb.resume_torrent(dl.hash)
        logger.info("Resumed torrent %s", dl.hash)
    return JSONResponse(status_code=204, content={})


@router.delete("/{download_id}", status_code=204)
async def delete_download(download_id: int, withFiles: bool = False, db: Session = Depends(get_db)):
    dl = db.get(models.Download, download_id)
    if not dl:
        raise HTTPException(404, "Not found")
    if dl.hash:
        async with _qb() as qb:
            await qb.login()
            logger.info("Deleting torrent %s (files=%s)", dl.hash, withFiles)
            await qb.delete_torrent(dl.hash, withFiles)
            logger.info("Deleted torrent %s", dl.hash)
    db.delete(dl)
    db.commit()
    return JSONResponse(status_code=204, content={})

