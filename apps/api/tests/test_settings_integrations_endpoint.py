from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import settings as settings_endpoints


def test_get_integrations_masks_secrets(monkeypatch):
    app = FastAPI()
    app.include_router(settings_endpoints.router, prefix="")

    monkeypatch.setattr(
        settings_endpoints.runtime_integration_settings,
        "describe",
        lambda include_secrets=False: {
            "tmdb.api_key": {
                "label": "TMDb API Key",
                "required": False,
                "masked_at_rest": True,
                "validation_rule": "min_length:16",
                "configured": True,
                "value": "••••••••" if not include_secrets else "raw-secret",
            }
        },
    )

    client = TestClient(app)
    response = client.get("/settings/integrations")

    assert response.status_code == 200
    payload = response.json()
    assert payload["integrations"] == [
        {
            "key": "tmdb.api_key",
            "label": "TMDb API Key",
            "required": False,
            "masked_at_rest": True,
            "validation_rule": "min_length:16",
            "configured": True,
            "value": "••••••••",
        }
    ]
    assert "providers" in payload


def test_update_integration_returns_validation_error(monkeypatch):
    app = FastAPI()
    app.include_router(settings_endpoints.router, prefix="")

    monkeypatch.setattr(
        settings_endpoints.runtime_integration_settings,
        "set",
        lambda _key, _value: (_ for _ in ()).throw(ValueError("bad value")),
    )

    client = TestClient(app)
    response = client.post(
        "/settings/integrations/tmdb.api_key",
        json={"value": "short"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "validation_failed"


def test_patch_integrations_accepts_partial_provider_updates(monkeypatch):
    app = FastAPI()
    app.include_router(settings_endpoints.router, prefix="")

    captured: dict[str, str | None] = {}

    def update_many(values):
        captured.update(values)
        return True

    monkeypatch.setattr(settings_endpoints.runtime_integration_settings, "update_many", update_many)

    client = TestClient(app)
    response = client.patch(
        "/settings/integrations",
        json={
            "providers": {
                "tmdb": {"values": {"api_key": "1234567890abcdef"}},
                "musicbrainz": {"values": {"user_agent": "Phelia/1.0 (dev@example.com)"}},
            }
        },
    )

    assert response.status_code == 200
    assert captured == {
        "tmdb.api_key": "1234567890abcdef",
        "musicbrainz.user_agent": "Phelia/1.0 (dev@example.com)",
    }


def test_patch_integrations_partial_update_preserves_existing_secrets(monkeypatch):
    app = FastAPI()
    app.include_router(settings_endpoints.router, prefix="")

    persisted_values = {
        "tmdb.api_key": "existing-secret-value",
        "musicbrainz.user_agent": "old-agent",
    }

    def update_many(values):
        persisted_values.update(values)
        return True

    monkeypatch.setattr(settings_endpoints.runtime_integration_settings, "update_many", update_many)

    client = TestClient(app)
    response = client.patch(
        "/settings/integrations",
        json={"providers": {"musicbrainz": {"values": {"user_agent": "new-agent"}}}},
    )

    assert response.status_code == 200
    assert persisted_values["tmdb.api_key"] == "existing-secret-value"
    assert persisted_values["musicbrainz.user_agent"] == "new-agent"


def test_patch_integrations_rejects_unknown_provider_field():
    app = FastAPI()
    app.include_router(settings_endpoints.router, prefix="")

    client = TestClient(app)
    response = client.patch(
        "/settings/integrations",
        json={"providers": {"tmdb": {"values": {"unknown": "value"}}}},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == {
        "error": "integration_not_found",
        "provider": "tmdb",
        "field": "unknown",
        "integration_key": "tmdb.unknown",
        "message": "Unknown field 'unknown' for provider 'tmdb'",
    }


def test_patch_integrations_rejects_empty_provider_payload():
    app = FastAPI()
    app.include_router(settings_endpoints.router, prefix="")

    client = TestClient(app)
    response = client.patch(
        "/settings/integrations",
        json={"providers": {"tmdb": {"values": {}}}},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == {
        "error": "validation_failed",
        "provider": "tmdb",
        "message": "Provider payload must include at least one field",
    }
