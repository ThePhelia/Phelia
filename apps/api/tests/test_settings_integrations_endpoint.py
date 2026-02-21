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
    assert response.json() == {
        "integrations": [
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
    }


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
