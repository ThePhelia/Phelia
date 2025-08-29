from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from pathlib import Path
import asyncio
from app.db.session import session_scope
from app.db.models import Download
from app.core.security import get_current_user
from app.core.config import settings
from app.services.jobs.tasks import enqueue_magnet, poll_status
from app.services.bt.qbittorrent import QbClient

router = APIRouter(dependencies=[Depends(get_current_user)])

class DownloadIn(BaseModel):
    magnet: str
    savePath: str | None = None

@router.get("/downloads")
def list_downloads():
    with session_scope() as db:
        rows = db.query(Download).order_by(Download.created_at.desc()).all()
        return [
            {
                "id": r.id,
                "status": r.status,
                "progress": r.progress,
                "rateDown": r.rate_down,
                "rateUp": r.rate_up,
                "etaSec": r.eta_sec,
                "savePath": r.save_path,
                "client": r.client,
                "hash": r.client_torrent_id,
                "createdAt": r.created_at.isoformat(),
            }
            for r in rows
        ]

@router.post("/downloads")
def create_download(body: DownloadIn):
    save_path = body.savePath or settings.DEFAULT_SAVE_DIR
    allowed = [Path(p.strip()) for p in settings.ALLOWED_SAVE_DIRS.split(',')]
    save_path_obj = Path(save_path)
    if not any(str(save_path_obj).startswith(str(a)) for a in allowed):
        raise HTTPException(status_code=400, detail=f"savePath not allowed. Allowed: {allowed}")
    try:
        save_path_obj.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot create directory: {e}")

    with session_scope() as db:
        dl = Download(save_path=str(save_path_obj), status="queued")
        db.add(dl)
        db.flush()
        enqueue_magnet.delay(dl.id, body.magnet, str(save_path_obj))
        return {"id": dl.id}

@router.get("/downloads/{download_id}")
def get_download(download_id: int):
    with session_scope() as db:
        dl = db.get(Download, download_id)
        if not dl:
            raise HTTPException(status_code=404, detail="Not found")
        poll_status.delay(download_id)
        return {
            "id": dl.id,
            "status": dl.status,
            "progress": dl.progress,
            "rateDown": dl.rate_down,
            "rateUp": dl.rate_up,
            "etaSec": dl.eta_sec,
            "savePath": dl.save_path,
            "client": dl.client,
            "hash": dl.client_torrent_id,
        }

@router.post("/downloads/{download_id}/pause")
async def pause_download(download_id: int):
    with session_scope() as db:
        dl = db.get(Download, download_id)
        if not dl:
            raise HTTPException(status_code=404, detail="Not found")
        if not dl.client_torrent_id:
            raise HTTPException(status_code=409, detail="Torrent hash not yet known; try again soon")
    qb = QbClient(settings.QB_URL, settings.QB_USER, settings.QB_PASS)
    await qb.pause(dl.client_torrent_id)
    return {"ok": True}

@router.post("/downloads/{download_id}/resume")
async def resume_download(download_id: int):
    with session_scope() as db:
        dl = db.get(Download, download_id)
        if not dl:
            raise HTTPException(status_code=404, detail="Not found")
        if not dl.client_torrent_id:
            raise HTTPException(status_code=409, detail="Torrent hash not yet known; try again soon")
    qb = QbClient(settings.QB_URL, settings.QB_USER, settings.QB_PASS)
    await qb.resume(dl.client_torrent_id)
    return {"ok": True}

@router.delete("/downloads/{download_id}")
async def delete_download(download_id: int, deleteFiles: bool = False):
    with session_scope() as db:
        dl = db.get(Download, download_id)
        if not dl:
            raise HTTPException(status_code=404, detail="Not found")
        if not dl.client_torrent_id:
            raise HTTPException(status_code=409, detail="Torrent hash not yet known; try again soon")
    qb = QbClient(settings.QB_URL, settings.QB_USER, settings.QB_PASS)
    await qb.delete(dl.client_torrent_id, delete_files=deleteFiles)
    # Обновим статус локально
    with session_scope() as db:
        dl = db.get(Download, download_id)
        dl.status = "cancelled"
        dl.progress = 0.0
    return {"ok": True}

# --- WebSocket: живой статус конкретной загрузки ---
@router.websocket("/ws/downloads/{download_id}")
async def ws_download_status(websocket: WebSocket, download_id: int):
    await websocket.accept()
    try:
        while True:
            # каждые 2 сек тянем актуальные данные из qBittorrent
            with session_scope() as db:
                dl = db.get(Download, download_id)
                if not dl:
                    await websocket.send_json({"error": "not_found"})
                    break
                torrent_hash = dl.client_torrent_id
            qb = QbClient(settings.QB_URL, settings.QB_USER, settings.QB_PASS)
            if torrent_hash:
                info = await qb.info_by_hash(torrent_hash)
                if info:
                    payload = {
                        "id": download_id,
                        "hash": torrent_hash,
                        "state": info.get("state"),
                        "progress": info.get("progress"),
                        "dlspeed": info.get("dlspeed"),
                        "upspeed": info.get("upspeed"),
                        "eta": info.get("eta"),
                        "name": info.get("name"),
                    }
                    await websocket.send_json(payload)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return
