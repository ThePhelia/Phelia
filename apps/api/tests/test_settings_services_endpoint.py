from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import settings as settings_endpoints


class Snapshot:
    def __init__(self, url: str, api_key: str | None):
        self.url = url
        self.api_key = api_key


def test_deprecated_jackett_alias_updates_prowlarr(monkeypatch):
    app = FastAPI()
    app.include_router(settings_endpoints.router, prefix="")

    state = {"url": "http://prowlarr:9696", "api_key": None}

    def update_prowlarr(*, url=None, api_key=None):
        if url is not None:
            state["url"] = url
        if api_key is not None:
            state["api_key"] = api_key
        return True

    def prowlarr_snapshot():
        return Snapshot(url=state["url"], api_key=state["api_key"])

    monkeypatch.setattr(settings_endpoints.runtime_service_settings, "update_prowlarr", update_prowlarr)
    monkeypatch.setattr(settings_endpoints.runtime_service_settings, "prowlarr_snapshot", prowlarr_snapshot)
    monkeypatch.setattr(settings_endpoints, "_refresh_prowlarr_provider", lambda: None)

    client = TestClient(app)
    response = client.post(
        "/settings/services/jackett",
        json={"url": "http://prowlarr.local", "api_key": "key123"},
    )

    assert response.status_code == 200
    assert response.headers["Warning"].startswith("299")
    assert response.json() == {
        "url": "http://prowlarr.local",
        "api_key_configured": True,
    }
