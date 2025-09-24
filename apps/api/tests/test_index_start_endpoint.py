import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import index as index_endpoints
from app.schemas.meta import CanonicalAlbum, CanonicalMovie, CanonicalTV, StartIndexingPayload


class DummyAdapter:
    def __init__(self):
        self.calls: list[tuple[str, list[int] | None]] = []

    async def search(self, query: str, categories: list[int] | None = None):
        self.calls.append((query, categories))
        return [
            {
                "title": "Example Release",
                "size": "1.4 GB",
                "seeders": 120,
                "leechers": 4,
                "tracker": "TrackerA",
                "magnet": "magnet:?xt=urn:btih:example",
                "link": "https://tracker.invalid/torrent",
            }
        ]


def build_app(adapter: DummyAdapter, monkeypatch):
    app = FastAPI()
    app.include_router(index_endpoints.router, prefix="/index")
    monkeypatch.setattr(index_endpoints, "JackettAdapter", lambda: adapter)
    monkeypatch.setattr(index_endpoints.jobs_tasks.index_with_jackett, "delay", lambda payload: payload)
    return app


@pytest.mark.anyio
async def test_index_builds_movie_query(monkeypatch):
    adapter = DummyAdapter()
    app = build_app(adapter, monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/index/start",
            json=StartIndexingPayload(
                type="movie",
                canonicalTitle="Blade Runner",
                movie=CanonicalMovie(title="Blade Runner", year=1982),
            ).model_dump(),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "Blade Runner 1982"
    assert adapter.calls[0][0] == "Blade Runner 1982"
    assert adapter.calls[0][1] == [2000, 5000]


@pytest.mark.anyio
async def test_index_builds_tv_query(monkeypatch):
    adapter = DummyAdapter()
    app = build_app(adapter, monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/index/start",
            json=StartIndexingPayload(
                type="tv",
                canonicalTitle="The Wire",
                tv=CanonicalTV(title="The Wire", season=1, episode=1),
            ).model_dump(),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "The Wire S01E01"
    assert adapter.calls[0][1] == [5000]


@pytest.mark.anyio
async def test_index_builds_album_query(monkeypatch):
    adapter = DummyAdapter()
    app = build_app(adapter, monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/index/start",
            json=StartIndexingPayload(
                type="album",
                canonicalTitle="Discovery",
                album=CanonicalAlbum(artist="Daft Punk", album="Discovery", year=2001),
            ).model_dump(),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "Daft Punk - Discovery 2001"
    assert adapter.calls[0][1] == [3000]
