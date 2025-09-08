from __future__ import annotations
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
def pause_download(download_id: int, db: Session = Depends(get_db)):
    dl = db.query(models.Download).get(download_id)
    if not dl:
        raise HTTPException(404, "Not found")
    if not dl.hash:
        raise HTTPException(409, "hash is not assigned yet")
    qb = _qb()
    qb.login()
    qb._c().post(f"{qb.base_url}/api/v2/torrents/pause", data={"hashes": dl.hash}).raise_for_status()
    return {}


@router.post("/{download_id}/resume", status_code=204)
def resume_download(download_id: int, db: Session = Depends(get_db)):
    dl = db.query(models.Download).get(download_id)
    if not dl:
        raise HTTPException(404, "Not found")
    if not dl.hash:
        raise HTTPException(409, "hash is not assigned yet")
    qb = _qb()
    qb.login()
    qb._c().post(f"{qb.base_url}/api/v2/torrents/resume", data={"hashes": dl.hash}).raise_for_status()
    return {}


@router.delete("/{download_id}", status_code=204)
def delete_download(download_id: int, withFiles: bool = False, db: Session = Depends(get_db)):
    dl = db.query(models.Download).get(download_id)
    if not dl:
        raise HTTPException(404, "Not found")
    if dl.hash:
        qb = _qb()
        qb.login()
        qb._c().post(
            f"{qb.base_url}/api/v2/torrents/delete",
            data={"hashes": dl.hash, "deleteFiles": "true" if withFiles else "false"},
        ).raise_for_status()
    db.delete(dl)
    db.commit()
    return {}

