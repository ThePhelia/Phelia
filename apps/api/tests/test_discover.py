import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import discover
from app.services.metadata.constants import TMDB_IMAGE_BASE


class FakeMetadataClient:
    def __init__(self, payloads: dict[str, dict]):
        self.payloads = payloads
        self.calls: list[tuple[str, dict]] = []

    async def tmdb(self, path: str, params: dict | None = None, request_id: str | None = None):
        self.calls.append((path, params or {}))
        return self.payloads.get(path, {})

    async def lastfm(self, method: str, params: dict | None = None, request_id: str | None = None):
        self.calls.append((method, params or {}))
        return self.payloads.get(method, {})


@pytest.mark.anyio
async def test_discover_movies_happy_path(monkeypatch):
    payloads = {
        "search/movie": {
            "page": 1,
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
    }
    fake_client = FakeMetadataClient(payloads)
    monkeypatch.setattr(discover, "get_metadata_client", lambda: fake_client)

    app = FastAPI()
    app.include_router(discover.router, prefix="/api/v1")

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
    assert fake_client.calls[0][0] == "search/movie"


@pytest.mark.anyio
async def test_discover_tv_happy_path(monkeypatch):
    payloads = {
        "search/tv": {
            "page": 2,
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
    }
    fake_client = FakeMetadataClient(payloads)
    monkeypatch.setattr(discover, "get_metadata_client", lambda: fake_client)

    app = FastAPI()
    app.include_router(discover.router, prefix="/api/v1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/discover/tv", params={"sort": "popular", "page": 2})

    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
    assert data["total_pages"] == 2
    assert data["items"][0]["kind"] == "tv"
    assert data["items"][0]["backdrop"] == f"{TMDB_IMAGE_BASE}/tv_backdrop.jpg"
    assert data["items"][0]["year"] == 2021
    assert data["items"][0]["meta"]["source"] == "tmdb"
    assert fake_client.calls[0][0] == "search/tv"


@pytest.mark.anyio
async def test_discover_albums_happy_path(monkeypatch):
    payloads = {
        "chart.gettopalbums": {
            "topalbums": {
                "@attr": {"page": "1", "totalPages": "3"},
                "album": [
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
            }
        }
    }

    class FakeMBClient:
        def __init__(self):
            self.seen: list[tuple[str | None, str]] = []

        async def lookup_release_group(self, artist, album, year=None):
            self.seen.append((artist, album))
            return {
                "artist": {"id": "artist-mb-1"},
                "release_group": {
                    "id": "rg-1",
                    "first_release_date": "2005-08-30",
                    "primary_type": "Album",
                },
            }

    fake_metadata = FakeMetadataClient(payloads)
    fake_mb = FakeMBClient()
    monkeypatch.setattr(discover, "get_metadata_client", lambda: fake_metadata)
    monkeypatch.setattr(discover, "get_musicbrainz_client", lambda: fake_mb)

    app = FastAPI()
    app.include_router(discover.router, prefix="/api/v1")

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
    assert fake_metadata.calls[0][0] == "chart.gettopalbums"
