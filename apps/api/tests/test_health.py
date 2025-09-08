import os
import sys
import httpx
import pytest

# Ensure environment variables for Settings before importing the app
os.environ.setdefault("APP_SECRET", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("QB_URL", "http://localhost:8080")
os.environ.setdefault("QB_USER", "admin")
os.environ.setdefault("QB_PASS", "adminadmin")
os.environ.setdefault("ANYIO_BACKEND", "asyncio")

# Add apps/api to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from app.routers.health import router as health_router
from app.services.bt.qbittorrent import QbClient
from httpx import AsyncClient, ASGITransport

app = FastAPI()
app.include_router(health_router, prefix="/api/v1")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_ok(monkeypatch):
    async def fake_login(self):
        return None

    async def fake_list_torrents(self):
        return [{"name": "a"}, {"name": "b"}]

    monkeypatch.setattr(QbClient, "login", fake_login)
    monkeypatch.setattr(QbClient, "list_torrents", fake_list_torrents)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/health")

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "details": {"qbittorrent": {"ok": True, "count": 2}}}


@pytest.mark.anyio
async def test_health_qbittorrent_unreachable(monkeypatch):
    async def fake_login(self):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(QbClient, "login", fake_login)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/health")

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "details": {"qbittorrent": {"ok": False}}}


@pytest.mark.anyio
async def test_healthz_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/healthz")

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
