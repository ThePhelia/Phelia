from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import pytest
from contextlib import asynccontextmanager
from httpx import ASGITransport, AsyncClient

SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

MODULES = [
    "app.main",
    "app.config",
    "app.cache",
    "app.clients.tmdb",
    "app.clients",
    "app.http",
]


def _fresh_app():
    for name in MODULES:
        sys.modules.pop(name, None)
    main = import_module("app.main")
    return main.create_app()


@asynccontextmanager
async def lifespan(app):
    async with app.router.lifespan_context(app):
        yield


class DummyResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.status_code = 200
        self._payload = payload
        self.headers: dict[str, str] = {}

    def json(self) -> dict[str, object]:
        return self._payload

    @property
    def text(self) -> str:
        return "ok"


@pytest.mark.anyio
async def test_tmdb_proxy_caches(monkeypatch):
    monkeypatch.setenv("CACHE_BACKEND", "memory")
    monkeypatch.setenv("TMDB_API_KEY", "test_key")

    calls = {"count": 0}

    app = _fresh_app()
    from app.config import get_settings
    import app.clients.tmdb as tmdb_module

    get_settings.cache_clear()
    assert get_settings().tmdb_api_key == "test_key"
    assert tmdb_module._settings.tmdb_api_key == "test_key"

    async def fake_request_json(method, url, params=None, headers=None):
        calls["count"] += 1
        return DummyResponse({"id": 1, "title": "Example"})

    monkeypatch.setattr("app.http.request_json", fake_request_json)
    monkeypatch.setattr("app.clients.request_json", fake_request_json)
    import app.http as http_module

    assert http_module.request_json is fake_request_json

    async with lifespan(app):
        from app.cache import init_cache

        await init_cache(get_settings())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.get("/tmdb/movie/1")
            assert first.status_code == 200, first.text
            first_payload = first.json()
            assert first_payload["provider"] == "tmdb"
            assert first_payload["cached"] is False
            assert "fetched_at" in first_payload

            second = await client.get("/tmdb/movie/1")
            assert second.status_code == 200
            second_payload = second.json()
            assert second_payload["cached"] is True
            assert second_payload["provider"] == "tmdb"

    assert calls["count"] == 1
