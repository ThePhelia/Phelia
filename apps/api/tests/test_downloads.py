import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
import httpx
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.core.config import settings
from app.routers.downloads import router as downloads_router
from app.db import models
from app.db.session import get_db
from app.services.jobs.tasks import celery_app, enqueue_download
from app.services.jobs import tasks


@pytest.mark.anyio
async def test_create_download(monkeypatch, db_session):
    app = FastAPI()
    app.include_router(downloads_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    monkeypatch.setattr(
        celery_app,
        "send_task",
        MagicMock(return_value=SimpleNamespace(failed=lambda: False)),
    )

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/downloads",
            json={"magnet": "magnet:?xt=urn:btih:abcd"},
        )

    assert resp.status_code == 201
    assert db_session.query(models.Download).count() == 1


def test_download_defaults(db_session):
    """Row persists with default speeds set."""
    dl = models.Download(magnet="magnet:?xt=urn:btih:abcd", save_path="/downloads")
    db_session.add(dl)
    db_session.commit()
    db_session.refresh(dl)

    assert dl.dlspeed == 0
    assert dl.upspeed == 0


@pytest.mark.anyio
async def test_create_download_qb_unreachable(monkeypatch, db_session):
    app = FastAPI()
    app.include_router(downloads_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    class BadQB:
        def login(self):
            raise httpx.RequestError("boom")

    def fake_send_task(name, args):
        enqueue_download(*args)
        return SimpleNamespace(failed=lambda: False)

    monkeypatch.setattr(tasks, "_qb", lambda: BadQB())
    monkeypatch.setattr(celery_app, "send_task", fake_send_task)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/downloads",
            json={"magnet": "magnet:?xt=urn:btih:abcd"},
        )

    assert resp.status_code == 502
    dl = db_session.query(models.Download).first()
    assert dl.status == "error"


@pytest.mark.anyio
async def test_download_lookup(db_session):
    app = FastAPI()
    app.include_router(downloads_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
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
    assert db_session.get(models.Download, dl.id) is None


@pytest.mark.anyio
async def test_pause_resume_success(monkeypatch, db_session):
    app = FastAPI()
    app.include_router(downloads_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    dl = models.Download(
        magnet="magnet:?xt=urn:btih:abcd",
        hash="abcd1234",
        save_path="/downloads",
        status="downloading",
    )
    db_session.add(dl)
    db_session.commit()
    db_session.refresh(dl)

    pause_mock = AsyncMock()
    resume_mock = AsyncMock()
    login_mock = AsyncMock()

    @asynccontextmanager
    async def fake_qb():
        yield SimpleNamespace(
            login=login_mock,
            pause_torrent=pause_mock,
            resume_torrent=resume_mock,
        )

    monkeypatch.setattr("app.routers.downloads._qb", lambda: fake_qb())

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_pause = await ac.post(f"/api/v1/downloads/{dl.id}/pause")
        resp_resume = await ac.post(f"/api/v1/downloads/{dl.id}/resume")

    assert resp_pause.status_code == 204
    assert resp_pause.json() == {}
    assert pause_mock.await_count == 1
    assert pause_mock.await_args.args == (dl.hash,)

    assert resp_resume.status_code == 204
    assert resp_resume.json() == {}
    assert resume_mock.await_count == 1
    assert resume_mock.await_args.args == (dl.hash,)


@pytest.mark.anyio
async def test_pause_after_candidate_hash(monkeypatch, db_session):
    app = FastAPI()
    app.include_router(downloads_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    candidate = {"hash": "abcd1234", "name": "Test", "state": "downloading"}

    class FakeQB:
        def login(self):
            return None

        def add_magnet(self, magnet, save_path=None):
            return None

        def add_torrent_file(self, content, save_path=None):
            return None

        def list_torrents(self):
            return [dict(candidate, save_path=settings.DEFAULT_SAVE_DIR)]

        def close(self):
            return None

    monkeypatch.setattr(tasks, "_qb", lambda: FakeQB())
    monkeypatch.setattr(tasks, "_pick_candidate", lambda stats, dl: candidate)
    monkeypatch.setattr(tasks, "broadcast_download", lambda dl: None)

    def fake_send_task(name, args):
        enqueue_download(*args)
        return SimpleNamespace(failed=lambda: False)

    monkeypatch.setattr(celery_app, "send_task", fake_send_task)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_create = await ac.post(
            "/api/v1/downloads",
            json={"magnet": "magnet:?xt=urn:btih:abcd"},
        )

    assert resp_create.status_code == 201

    db_session.expire_all()
    dl = db_session.query(models.Download).first()
    assert dl.hash == candidate["hash"]

    pause_mock = AsyncMock()
    login_mock = AsyncMock()

    @asynccontextmanager
    async def fake_qb():
        yield SimpleNamespace(login=login_mock, pause_torrent=pause_mock)

    monkeypatch.setattr("app.routers.downloads._qb", lambda: fake_qb())

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_pause = await ac.post(f"/api/v1/downloads/{dl.id}/pause")

    assert resp_pause.status_code == 204
    assert pause_mock.await_count == 1
    assert pause_mock.await_args.args == (candidate["hash"],)
