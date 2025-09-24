import pytest
from fastapi import FastAPI
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import capabilities as capabilities_router
from app.core.runtime_settings import runtime_settings


class DummyQbClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover - nothing to clean up
        return None

    async def login(self):
        return None

    async def list_torrents(self):
        return []


@pytest.mark.anyio
async def test_capabilities_reports_service_status(monkeypatch):
    monkeypatch.setattr(capabilities_router, "QbClient", lambda *args, **kwargs: DummyQbClient())
    monkeypatch.setattr(capabilities_router.settings, "JACKETT_API_KEY", "secret")
    monkeypatch.setattr(capabilities_router.settings, "PHELIA_PUBLIC_BASE_URL", "http://public")
    runtime_settings.set("tmdb", "tmdb")
    runtime_settings.set("omdb", "omdb")
    runtime_settings.set("discogs", "discogs")
    runtime_settings.set("lastfm", "lastfm")

    app = FastAPI()
    app.include_router(capabilities_router.router, prefix="/api/v1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/capabilities")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["services"]["qbittorrent"] is True
    assert payload["services"]["jackett"] is True
    assert payload["links"]["jackett"] == capabilities_router.settings.jackett_public_url


@pytest.mark.anyio
async def test_capabilities_handles_qb_failure(monkeypatch):
    class FailingQb:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover - nothing to clean up
            return None

        async def login(self):  # pragma: no cover - triggered via test
            raise RuntimeError("boom")

        async def list_torrents(self):  # pragma: no cover - not reached
            return []

    monkeypatch.setattr(capabilities_router, "QbClient", lambda *args, **kwargs: FailingQb())

    app = FastAPI()
    app.include_router(capabilities_router.router, prefix="/api/v1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/capabilities")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["services"]["qbittorrent"] is False
