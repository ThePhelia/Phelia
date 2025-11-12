import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.routers.health import router as health_router
from app.services.bt.qbittorrent import QbClient

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
    assert resp.json() == {
        "ok": True,
        "details": {"qbittorrent": {"ok": True, "count": 2}},
    }


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
