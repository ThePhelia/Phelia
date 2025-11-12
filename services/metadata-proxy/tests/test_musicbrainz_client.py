from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from importlib import import_module
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.datastructures import QueryParams

SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

MODULES = [
    "app.main",
    "app.config",
    "app.cache",
    "app.clients.musicbrainz",
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


class DummyRequest:
    def __init__(self, query: str = "", headers: dict[str, str] | None = None) -> None:
        self.query_params = QueryParams(query)
        self.headers = headers or {}


class DummyResponse:
    def __init__(
        self,
        status_code: int,
        payload: object,
        *,
        headers: dict[str, str] | None = None,
        text: str | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        if text is not None:
            self._text = text
        elif isinstance(payload, (dict, list)):
            self._text = json.dumps(payload)
        else:
            self._text = str(payload)

    def json(self) -> object:
        return self._payload

    @property
    def text(self) -> str:
        return self._text


def test_mb_params_adds_fmt_when_missing():
    from app.clients.musicbrainz import _mb_params

    request = DummyRequest("artist=Radiohead")
    assert _mb_params(request, "artist", object()) == [("fmt", "json")]


def test_mb_params_keeps_existing_fmt():
    from app.clients.musicbrainz import _mb_params

    request = DummyRequest("fmt=json&artist=Radiohead")
    assert _mb_params(request, "artist", object()) == []


def test_mb_headers_uses_settings_user_agent(monkeypatch):
    monkeypatch.setenv("MB_USER_AGENT", "UnitTest/1.0 (+https://example.test)")
    from app.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()

    from app.clients.musicbrainz import _mb_headers

    headers = _mb_headers(DummyRequest(), "artist", settings)
    assert headers["user-agent"] == "UnitTest/1.0 (+https://example.test)"
    assert headers["accept"] == "application/json"


@pytest.mark.anyio
async def test_musicbrainz_proxy_caches(monkeypatch):
    monkeypatch.setenv("CACHE_BACKEND", "memory")
    monkeypatch.setenv("MB_USER_AGENT", "UnitTest/1.0 (+https://example.test)")

    calls: list[dict[str, object]] = []

    app = _fresh_app()
    from app.config import get_settings
    import app.clients.musicbrainz as mb_module

    get_settings.cache_clear()
    settings = get_settings()
    assert settings.mb_user_agent == "UnitTest/1.0 (+https://example.test)"
    assert mb_module._settings.mb_user_agent == "UnitTest/1.0 (+https://example.test)"

    async def fake_request_json(method, url, params=None, headers=None):
        calls.append(
            {"method": method, "url": url, "params": params, "headers": headers}
        )
        return DummyResponse(200, {"id": "123", "name": "Radiohead"})

    monkeypatch.setattr("app.http.request_json", fake_request_json)
    monkeypatch.setattr("app.clients.request_json", fake_request_json)

    async with lifespan(app):
        from app.cache import init_cache

        await init_cache(get_settings())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.get("/mb/artist", params={"query": "artist:Radiohead"})
            assert first.status_code == 200, first.text
            first_payload = first.json()
            assert first_payload["provider"] == "musicbrainz"
            assert first_payload["cached"] is False
            assert "fetched_at" in first_payload

            second = await client.get(
                "/mb/artist", params={"query": "artist:Radiohead"}
            )
            assert second.status_code == 200
            second_payload = second.json()
            assert second_payload["cached"] is True
            assert second_payload["provider"] == "musicbrainz"

    assert len(calls) == 1
    call = calls[0]
    params = call["params"]
    assert params is not None
    assert params.get("fmt") == "json"
    headers = call["headers"]
    assert headers["user-agent"] == mb_module._settings.mb_user_agent
    assert headers["accept"] == "application/json"


@pytest.mark.anyio
async def test_musicbrainz_proxy_propagates_errors(monkeypatch):
    monkeypatch.setenv("CACHE_BACKEND", "memory")
    monkeypatch.setenv("MB_USER_AGENT", "UnitTest/1.0 (+https://example.test)")

    app = _fresh_app()
    from app.config import get_settings

    get_settings.cache_clear()
    assert get_settings().mb_user_agent == "UnitTest/1.0 (+https://example.test)"

    async def fake_request_json(method, url, params=None, headers=None):
        return DummyResponse(503, {"error": "outage"}, text="temporary outage")

    monkeypatch.setattr("app.http.request_json", fake_request_json)
    monkeypatch.setattr("app.clients.request_json", fake_request_json)

    async with lifespan(app):
        from app.cache import init_cache

        await init_cache(get_settings())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/mb/artist", params={"query": "artist:Opeth"})
            assert response.status_code == 503
            detail = response.json().get("detail")
            assert detail["error"] == "upstream_error"
            assert detail["status"] == 503
            assert detail["message"] == "temporary outage"
