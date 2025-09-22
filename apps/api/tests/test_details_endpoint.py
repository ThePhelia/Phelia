import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import details as details_router
from app.db.session import get_db
from app.schemas.media import EnrichedCard
from app.schemas.ui import ListMutationInput, ListMutationItem
from app.services import library as library_service


class DummyRouter:
    def __init__(self, card: EnrichedCard):
        self._card = card

    async def enrich(self, classification, title):  # pragma: no cover - simple passthrough
        return self._card


@pytest.mark.anyio
async def test_details_returns_enriched_card(monkeypatch, db_session):
    app = FastAPI()
    app.include_router(details_router.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session

    mutation = ListMutationInput(
        action="add",
        list="watchlist",
        item=ListMutationItem(kind="movie", id="blade-runner-2049", title="Blade Runner 2049", year=2017),
    )
    library_service.apply_mutation(db_session, mutation)

    card = EnrichedCard(
        media_type="movie",
        confidence=0.9,
        title="Blade Runner 2049",
        parsed={"year": 2017},
        ids={"tmdb_id": 101, "imdb_id": "tt1856101"},
        details={
            "tmdb": {
                "title": "Blade Runner 2049",
                "year": 2017,
                "overview": "Officer K discovers a secret.",
                "poster": "http://example/poster.jpg",
                "backdrop": "http://example/backdrop.jpg",
                "extra": {
                    "tmdb": {
                        "tagline": "The key to the future is finally unearthed.",
                        "genres": [{"name": "Science Fiction"}],
                        "credits": {
                            "cast": [
                                {
                                    "name": "Ryan Gosling",
                                    "character": "K",
                                    "profile_path": "/ryan.jpg",
                                }
                            ],
                            "crew": [{"name": "Denis Villeneuve", "job": "Director"}],
                        },
                        "similar": {
                            "results": [
                                {"id": 102, "title": "Arrival", "poster_path": "/arrival.jpg"}
                            ]
                        },
                        "recommendations": {
                            "results": [
                                {
                                    "id": 103,
                                    "title": "Dune",
                                    "poster_path": "/dune.jpg",
                                }
                            ]
                        },
                        "seasons": [],
                    }
                },
            },
            "omdb": {"imdbRating": "8.0"},
            "discogs": {},
        },
        providers=[],
        reasons=[],
        needs_confirmation=False,
    )

    monkeypatch.setattr(details_router, "get_metadata_router", lambda: DummyRouter(card))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/details/movie/blade-runner-2049")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["title"] == "Blade Runner 2049"
    assert payload["genres"] == ["Science Fiction"]
    assert payload["cast"][0]["name"] == "Ryan Gosling"
    assert payload["similar"][0]["title"] == "Arrival"
    assert payload["recommended"][0]["title"] == "Dune"


@pytest.mark.anyio
async def test_details_returns_when_tmdb_missing(monkeypatch, db_session):
    app = FastAPI()
    app.include_router(details_router.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session

    mutation = ListMutationInput(
        action="add",
        list="watchlist",
        item=ListMutationItem(
            kind="movie", id="blade-runner-2049", title="Blade Runner 2049", year=2017
        ),
    )
    library_service.apply_mutation(db_session, mutation)

    card = EnrichedCard(
        media_type="movie",
        confidence=0.9,
        title="Blade Runner 2049",
        parsed={"year": 2017},
        ids={},
        details={
            "lastfm": {"summary": "Officer K discovers a secret."},
            "discogs": {
                "cover_image": "http://example/discogs.jpg",
                "extra": {
                    "tracklist": [
                        {"title": "2049", "duration": "03:36"},
                        {"title": "Sapper's Tree", "duration": "04:53"},
                    ]
                },
            },
        },
        providers=[],
        reasons=[],
        needs_confirmation=False,
    )

    monkeypatch.setattr(details_router, "get_metadata_router", lambda: DummyRouter(card))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/details/movie/blade-runner-2049")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["title"] == "Blade Runner 2049"
    assert payload["overview"] == "Officer K discovers a secret."
    assert payload["poster"] == "http://example/discogs.jpg"
    assert [track["title"] for track in payload.get("tracks", [])] == [
        "2049",
        "Sapper's Tree",
    ]


@pytest.mark.anyio
async def test_details_handles_metadata_failure(monkeypatch, db_session):
    app = FastAPI()
    app.include_router(details_router.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session

    mutation = ListMutationInput(
        action="add",
        list="watchlist",
        item=ListMutationItem(kind="movie", id="error-case", title="Error Case"),
    )
    library_service.apply_mutation(db_session, mutation)

    class FailingRouter:
        async def enrich(self, classification, title):  # pragma: no cover - exercised via test
            raise RuntimeError("boom")

    monkeypatch.setattr(details_router, "get_metadata_router", lambda: FailingRouter())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/details/movie/error-case")

    assert resp.status_code == 502
    assert resp.json()["detail"] == "metadata_error"
