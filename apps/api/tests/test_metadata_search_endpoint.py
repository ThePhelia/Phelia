import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints.search import get_provider, router
from app.ext.interfaces import ProviderDescriptor, SearchProvider
from app.schemas.media import EnrichedCard


class DummyProvider(SearchProvider):
    slug = "dummy"
    name = "Dummy search"

    def __init__(self, cards, meta):
        self.cards = cards
        self.meta = meta
        self.calls = []

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            slug=self.slug,
            name=self.name,
            kind="search",
            configured=True,
            healthy=True,
        )

    async def search(self, query: str, *, limit: int, kind: str):
        self.calls.append((query, limit, kind))
        return self.cards, self.meta


def build_app(provider: DummyProvider) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="")
    app.dependency_overrides[get_provider] = lambda: provider
    return app


@pytest.mark.anyio
async def test_search_transforms_cards():
    movie_card = EnrichedCard(
        media_type="movie",
        confidence=0.92,
        title="Example Torrent 1080p",
        ids={"tmdb_id": 123, "imdb_id": "tt123"},
        details={
            "tmdb": {
                "title": "Example Movie",
                "year": 1999,
                "poster": "https://images.example/movie.jpg",
                "backdrop": "https://images.example/movie-bg.jpg",
            },
            "images": {
                "poster": "https://images.example/movie.jpg",
                "backdrop": "https://images.example/movie-bg.jpg",
            },
        },
        reasons=["tmdb_match"],
    )

    album_card = EnrichedCard(
        media_type="music",
        confidence=0.81,
        title="Radiohead - In Rainbows (2007)",
        parsed={"artist": "Radiohead", "year": 2007},
        ids={"mb_release_group_id": "rg-1"},
        details={
            "musicbrainz": {
                "id": "rg-1",
                "first_release_date": "2007-10-10",
                "title": "In Rainbows",
            },
            "discogs": {
                "id": 55,
                "title": "In Rainbows",
                "cover_image": "https://images.example/in-rainbows.jpg",
                "year": 2007,
            },
            "tags": ["Alternative", "Rock"],
        },
    )

    provider = DummyProvider([movie_card, album_card], {"message": "dummy meta"})
    app = build_app(provider)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/search", params={"q": "example"})

    assert response.status_code == 200
    payload = response.json()

    assert payload["page"] == 1
    assert payload["total_pages"] == 1
    assert payload.get("message") == "dummy meta"

    assert len(payload["items"]) == 2

    movie = next(item for item in payload["items"] if item["kind"] == "movie")
    album = next(item for item in payload["items"] if item["kind"] == "album")

    assert movie["id"] == "123"
    assert movie["title"] == "Example Movie"
    assert movie["poster"] == "https://images.example/movie.jpg"
    assert movie["meta"]["confidence"] == pytest.approx(0.92)
    assert "providers" in movie["meta"]

    assert album["id"] == "rg-1"
    assert album["title"] == "In Rainbows"
    assert album["subtitle"] == "Radiohead"
    assert album["poster"] == "https://images.example/in-rainbows.jpg"
    assert set(album["genres"]) == {"Alternative", "Rock"}
    assert album["meta"]["source_kind"] == "music"
    assert "providers" in album["meta"]

    # Adapter should have been invoked with the requested query and default pagination.
    assert provider.calls == [("example", 40, "all")]
