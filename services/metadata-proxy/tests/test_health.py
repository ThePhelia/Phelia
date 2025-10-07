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


@pytest.mark.anyio
async def test_health_endpoint(monkeypatch):
    monkeypatch.setenv("CACHE_BACKEND", "memory")
    app = _fresh_app()
    async with lifespan(app):
        from app.cache import init_cache
        from app.config import get_settings

        await init_cache(get_settings())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
