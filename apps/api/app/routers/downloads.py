from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.session import session_scope
from app.db.models import Download
from app.core.config import settings
from app.services.jobs.tasks import enqueue_magnet, poll_status

router = APIRouter()

class DownloadIn(BaseModel):
    magnet: str
    savePath: str | None = None

@router.post("/downloads")
def create_download(body: DownloadIn):
    save_path = body.savePath or settings.DEFAULT_SAVE_DIR
    # очень простая проверка пути — whitelist
    allowed = [p.strip() for p in settings.ALLOWED_SAVE_DIRS.split(',')]
    if not any(save_path.startswith(a) for a in allowed):
        raise HTTPException(status_code=400, detail=f"savePath not allowed. Allowed: {allowed}")

    with session_scope() as db:
        dl = Download(save_path=save_path, status="queued")
        db.add(dl)
        db.flush()
        enqueue_magnet.delay(dl.id, body.magnet, save_path)
        return {"id": dl.id}

@router.get("/downloads/{download_id}")
def get_download(download_id: int):
    with session_scope() as db:
        dl = db.get(Download, download_id)
        if not dl:
            raise HTTPException(status_code=404, detail="Not found")
        # kick a poll for freshness
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
        }
