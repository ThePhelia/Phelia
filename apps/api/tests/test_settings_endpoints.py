import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import capabilities as capabilities_router
from app.api.v1.endpoints import settings as settings_router
from app.core.config import settings
from app.db.models import ProviderCredential
from app.db.session import get_db
from app.services import settings as settings_service


class DummyQbClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover - nothing to clean up
        return None

    async def login(self):  # pragma: no cover - exercised via test
        return None

    async def list_torrents(self):  # pragma: no cover - exercised via test
        return []


def test_load_provider_credentials_populates_settings(db_session, monkeypatch):
    db_session.add(ProviderCredential(provider="tmdb", api_key="tmdb-key"))
    db_session.add(ProviderCredential(provider="omdb", api_key="omdb-key"))
    db_session.commit()

    monkeypatch.setattr(settings, "TMDB_API_KEY", None)
    monkeypatch.setattr(settings, "OMDB_API_KEY", None)

    cleared: list[bool] = []

    def fake_clear():
        cleared.append(True)

    monkeypatch.setattr(settings_service.get_metadata_router, "cache_clear", fake_clear)

    applied = settings_service.load_provider_credentials(db_session)

    assert settings.TMDB_API_KEY == "tmdb-key"
    assert settings.OMDB_API_KEY == "omdb-key"
    assert applied == {"tmdb": "tmdb-key", "omdb": "omdb-key"}
    assert cleared  # cache clear triggered


@pytest.mark.anyio
async def test_settings_router_updates_credentials(db_session, monkeypatch):
    monkeypatch.setattr(settings_service.get_metadata_router, "cache_clear", lambda: None)
    monkeypatch.setattr(capabilities_router, "QbClient", lambda *args, **kwargs: DummyQbClient())
    monkeypatch.setattr(settings, "TMDB_API_KEY", None)

    app = FastAPI()
    app.include_router(settings_router.router, prefix="/api/v1")
    app.include_router(capabilities_router.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/settings/providers")
        assert resp.status_code == 200
        providers = {row["provider"]: row for row in resp.json()["providers"]}
        assert providers["tmdb"]["configured"] is False

        resp = await client.put(
            "/api/v1/settings/providers/tmdb",
            json={"api_key": "tmdb-secret"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["provider"] == "tmdb"
        assert body["configured"] is True
        assert body["masked_api_key"].endswith("cret")

        resp = await client.get("/api/v1/capabilities")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["services"]["tmdb"] is True

        resp = await client.get("/api/v1/settings/providers")
        providers = {row["provider"]: row for row in resp.json()["providers"]}
        assert providers["tmdb"]["configured"] is True
        assert providers["tmdb"]["masked_api_key"].endswith("cret")


@pytest.mark.anyio
async def test_settings_router_rejects_unknown_provider(db_session):
    app = FastAPI()
    app.include_router(settings_router.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.put(
            "/api/v1/settings/providers/unknown",
            json={"api_key": "value"},
        )
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"] == "unknown_provider"
