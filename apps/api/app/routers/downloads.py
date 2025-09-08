from __future__ import annotations
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models
from app.core.config import settings
from app.services.jobs.tasks import celery_app
from app.services.bt.qbittorrent import QbClient


router = APIRouter(prefix="/downloads", tags=["downloads"])


class DownloadCreate(BaseModel):
    magnet: str = Field(min_length=10)
    savePath: Optional[str] = None


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
    dl = models.Download(magnet=body.magnet, save_path=save_path, status="queued")
    db.add(dl)
    db.commit()
    db.refresh(dl)
    celery_app.send_task(
        "app.services.jobs.tasks.enqueue_magnet",
        args=[dl.id, body.magnet, save_path],
    )
    return {"id": dl.id}


@router.post("/{download_id}/pause", status_code=204)
async def pause_download(download_id: int, db: Session = Depends(get_db)):
    dl = db.get(models.Download, download_id)
    if not dl:
        raise HTTPException(404, "Not found")
    if not dl.hash:
        raise HTTPException(409, "hash is not assigned yet")
<<<<<<< ours
    qb = _qb()
    await qb.login()
    await qb.pause_torrent(dl.hash)
    return {}
=======
    async with _qb() as qb:
        await qb.login()
        await qb.pause_torrent(dl.hash)
    return JSONResponse(status_code=204, content={})
>>>>>>> theirs


@router.post("/{download_id}/resume", status_code=204)
async def resume_download(download_id: int, db: Session = Depends(get_db)):
    dl = db.get(models.Download, download_id)
    if not dl:
        raise HTTPException(404, "Not found")
    if not dl.hash:
        raise HTTPException(409, "hash is not assigned yet")
<<<<<<< ours
    qb = _qb()
    await qb.login()
    await qb.resume_torrent(dl.hash)
    return {}
=======
    async with _qb() as qb:
        await qb.login()
        await qb.resume_torrent(dl.hash)
    return JSONResponse(status_code=204, content={})
>>>>>>> theirs


@router.delete("/{download_id}", status_code=204)
async def delete_download(download_id: int, withFiles: bool = False, db: Session = Depends(get_db)):
    dl = db.get(models.Download, download_id)
    if not dl:
        raise HTTPException(404, "Not found")
    if dl.hash:
<<<<<<< ours
        qb = _qb()
        await qb.login()
        await qb.delete_torrent(dl.hash, withFiles)
=======
        async with _qb() as qb:
            await qb.login()
            await qb.delete_torrent(dl.hash, withFiles)
>>>>>>> theirs
    db.delete(dl)
    db.commit()
    return JSONResponse(status_code=204, content={})

