import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.routers.downloads import router as downloads_router
from app.db import models
from app.db.session import SessionLocal


@pytest.mark.anyio
async def test_download_lookup(db_session):
    app = FastAPI()
    app.include_router(downloads_router, prefix="/api/v1")
    transport = ASGITransport(app=app)

    # Not found case
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_nf = await ac.post("/api/v1/downloads/1/pause")
    assert resp_nf.status_code == 404

    # Create download without hash
    dl = models.Download(magnet="magnet:?xt=urn:btih:abcd", save_path="/downloads", status="queued")
    db_session.add(dl)
    db_session.commit()
    db_session.refresh(dl)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_conflict = await ac.post(f"/api/v1/downloads/{dl.id}/pause")
        resp_delete = await ac.delete(f"/api/v1/downloads/{dl.id}")

    assert resp_conflict.status_code == 409
    assert resp_delete.status_code == 204

    with SessionLocal() as db:
        assert db.get(models.Download, dl.id) is None
