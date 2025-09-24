import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, MockTransport, Response

from app.api.v1.endpoints import discover
from app.api.v1.endpoints import settings as settings_router
from app.db.session import get_db
from app.services.metadata.providers.tmdb import TMDB_IMAGE_BASE


@pytest.mark.anyio
async def test_discover_movies_happy_path():
    class FakeTMDBClient:
        async def discover_media(self, media_type, sort, page):  # noqa: D401 - simple stub
            assert media_type == "movie"
            assert sort == "trending"
            assert page == 1
            return {
                "page": page,
                "total_pages": 5,
                "results": [
                    {
                        "id": 101,
                        "title": "Example Movie",
                        "overview": "A delightful test fixture.",
                        "release_date": "2023-03-14",
                        "poster_path": "/poster.jpg",
                        "backdrop_path": "/backdrop.jpg",
                        "vote_average": 7.8,
                        "vote_count": 42,
                        "popularity": 123.4,
                    }
                ],
            }

    app = FastAPI()
    app.include_router(discover.router, prefix="/api/v1")
    app.dependency_overrides[discover.get_tmdb_client] = lambda: FakeTMDBClient()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/discover/movie")

    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["total_pages"] == 5
    assert data["items"][0]["kind"] == "movie"
    assert data["items"][0]["title"] == "Example Movie"
    assert data["items"][0]["poster"] == f"{TMDB_IMAGE_BASE}/poster.jpg"
    assert data["items"][0]["year"] == 2023
    assert data["items"][0]["meta"]["source"] == "tmdb"


@pytest.mark.anyio
async def test_discover_tv_happy_path():
    class FakeTMDBClient:
        def __init__(self):
            self.calls: list[tuple[str, str, int]] = []

        async def discover_media(self, media_type, sort, page):
            self.calls.append((media_type, sort, page))
            return {
                "page": page,
                "total_pages": 2,
                "results": [
                    {
                        "id": 202,
                        "name": "Example Show",
                        "overview": "Serialized test data.",
                        "first_air_date": "2021-09-01",
                        "poster_path": None,
                        "backdrop_path": "/tv_backdrop.jpg",
                        "vote_average": 8.1,
                        "vote_count": 84,
                        "popularity": 321.0,
                    }
                ],
            }

    fake_client = FakeTMDBClient()

    app = FastAPI()
    app.include_router(discover.router, prefix="/api/v1")
    app.dependency_overrides[discover.get_tmdb_client] = lambda: fake_client

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/discover/tv", params={"sort": "popular", "page": 2})

    assert resp.status_code == 200
    data = resp.json()
    assert fake_client.calls == [("tv", "popular", 2)]
    assert data["page"] == 2
    assert data["total_pages"] == 2
    assert data["items"][0]["kind"] == "tv"
    assert data["items"][0]["backdrop"] == f"{TMDB_IMAGE_BASE}/tv_backdrop.jpg"
    assert data["items"][0]["year"] == 2021
    assert data["items"][0]["meta"]["source"] == "tmdb"


@pytest.mark.anyio
async def test_discover_albums_happy_path():
    class FakeLastFMClient:
        async def get_top_albums(self, page=1, limit=20):  # noqa: D401 - simple stub
            assert page == 1
            return {
                "items": [
                    {
                        "name": "Test Album",
                        "artist": {"name": "Test Artist", "mbid": "artist-1"},
                        "mbid": "album-1",
                        "playcount": "1234",
                        "listeners": "4321",
                        "image": [
                            {"#text": "http://image.small", "size": "small"},
                            {"#text": "http://image.large", "size": "large"},
                        ],
                        "@attr": {"rank": "1"},
                        "tags": {"tag": [{"name": "Indie"}]},
                        "url": "https://last.fm/music/Test+Artist/Test+Album",
                    }
                ],
                "page": 1,
                "total_pages": 3,
            }

    class FakeMBClient:
        def __init__(self):
            self.seen: list[tuple[str | None, str]] = []

        async def lookup_release_group(self, artist, album, year=None):  # noqa: D401 - simple stub
            self.seen.append((artist, album))
            return {
                "artist": {"id": "artist-mb-1"},
                "release_group": {
                    "id": "rg-1",
                    "first_release_date": "2005-08-30",
                    "primary_type": "Album",
                },
            }

    fake_lastfm = FakeLastFMClient()
    fake_mb = FakeMBClient()

    app = FastAPI()
    app.include_router(discover.router, prefix="/api/v1")
    app.dependency_overrides[discover.get_lastfm_client] = lambda: fake_lastfm
    app.dependency_overrides[discover.get_musicbrainz_client] = lambda: fake_mb

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/discover/album")

    assert resp.status_code == 200
    data = resp.json()
    assert fake_mb.seen == [("Test Artist", "Test Album")]
    assert data["page"] == 1
    assert data["total_pages"] == 3
    assert data["items"][0]["kind"] == "album"
    assert data["items"][0]["subtitle"] == "Test Artist"
    assert data["items"][0]["poster"] == "http://image.large"
    assert data["items"][0]["year"] == 2005
    assert data["items"][0]["meta"]["source"] == "lastfm"
    assert data["items"][0]["meta"]["musicbrainz"]["release_group_id"] == "rg-1"


@pytest.mark.anyio
async def test_discover_uses_tmdb_after_settings_update(db_session, monkeypatch):
    called_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> Response:  # pragma: no cover - simple mock handler
        called_requests.append(request)
        payload = {
            "page": 1,
            "total_pages": 1,
            "results": [
                {
                    "id": 42,
                    "title": "Runtime Updated",
                    "overview": "Fresh from TMDb",
                    "release_date": "2024-08-01",
                    "poster_path": "/poster.jpg",
                    "backdrop_path": "/backdrop.jpg",
                }
            ],
        }
        return Response(200, json=payload)

    mock_transport = MockTransport(handler)
    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs.setdefault("transport", mock_transport)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    app = FastAPI()
    app.include_router(settings_router.router, prefix="/api/v1")
    app.include_router(discover.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/discover/movie")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"][0]["meta"]["source"] == "fallback"
        assert not called_requests  # no outbound calls without key

        resp = await client.put(
            "/api/v1/settings/providers/tmdb",
            json={"apiKey": "runtime-key"},
        )
        assert resp.status_code == 200

        resp = await client.get("/api/v1/discover/movie")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"][0]["meta"]["source"] == "tmdb"
        assert data["items"][0]["title"] == "Runtime Updated"
        assert called_requests
        request = called_requests[0]
        assert request.url.params["api_key"] == "runtime-key"
