import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import library as library_router
from app.db.session import get_db


@pytest.mark.anyio
async def test_library_add_remove_cycle(db_session):
    app = FastAPI()
    app.include_router(library_router.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/library")
        assert resp.status_code == 200
        assert resp.json()["watchlist"] == []

        payload = {
            "action": "add",
            "list": "watchlist",
            "item": {
                "kind": "movie",
                "id": "blade-runner-2049",
                "title": "Blade Runner 2049",
                "year": 2017,
                "poster": "http://example/poster.jpg",
                "genres": ["Sci-Fi"],
            },
        }
        resp = await client.post("/api/v1/library/list", json=payload)
        assert resp.status_code == 200
        assert resp.json() == {"success": True}

        resp = await client.get("/api/v1/library")
        data = resp.json()
        assert len(data["watchlist"]) == 1
        assert data["watchlist"][0]["title"] == "Blade Runner 2049"

        payload["action"] = "remove"
        resp = await client.post("/api/v1/library/list", json=payload)
        assert resp.status_code == 200

        resp = await client.get("/api/v1/library")
        assert resp.json()["watchlist"] == []


@pytest.mark.anyio
async def test_library_playlist_requires_id(db_session):
    app = FastAPI()
    app.include_router(library_router.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/library/list",
            json={"action": "add", "list": "playlist", "item": {"kind": "movie", "id": "x"}},
        )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "playlist_id_required"
