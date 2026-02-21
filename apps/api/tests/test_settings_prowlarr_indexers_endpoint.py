from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import settings as settings_endpoints
from app.services.prowlarr_client import ProwlarrApiError


class FakeClient:
    def __init__(self):
        self.indexers = [
            {
                "id": 1,
                "name": "Demo",
                "enable": True,
                "implementation": "Cardigann",
                "implementationName": "Demo Impl",
                "protocol": "torrent",
                "fields": [{"name": "baseUrl", "label": "Base Url", "value": "https://example.com"}],
            }
        ]
        self.templates = [
            {
                "id": 10,
                "name": "Template",
                "implementation": "Cardigann",
                "implementationName": "Template Impl",
                "protocol": "torrent",
                "fields": [{"name": "baseUrl", "label": "Base Url", "value": ""}],
            }
        ]

    async def list_indexers(self):
        return self.indexers

    async def list_indexer_templates(self):
        return self.templates

    async def create_indexer(self, payload):
        return {**payload, "id": 99, "enable": True, "fields": payload.get("fields", [])}

    async def update_indexer(self, indexer_id, payload):
        return {**payload, "id": indexer_id}

    async def delete_indexer(self, indexer_id):
        return None

    async def test_indexer(self, payload):
        return {"ok": True, "name": payload.get("name")}


def build_client(monkeypatch, fake: FakeClient):
    app = FastAPI()
    app.include_router(settings_endpoints.router, prefix="")
    monkeypatch.setattr(settings_endpoints, "_autoload_prowlarr_api_key", lambda: None)

    async def _client():
        return fake

    monkeypatch.setattr(settings_endpoints, "_prowlarr_client", _client)
    return TestClient(app)


def test_list_indexers(monkeypatch):
    client = build_client(monkeypatch, FakeClient())
    response = client.get("/settings/services/prowlarr/indexers")
    assert response.status_code == 200
    assert response.json()["indexers"][0]["name"] == "Demo"


def test_create_indexer(monkeypatch):
    client = build_client(monkeypatch, FakeClient())
    response = client.post(
        "/settings/services/prowlarr/indexers",
        json={"template_id": 10, "name": "New Indexer", "settings": {"baseUrl": "https://new.example"}},
    )
    assert response.status_code == 200
    assert response.json()["id"] == 99


def test_prowlarr_error_passthrough(monkeypatch):
    fake = FakeClient()

    async def broken_list_indexers():
        raise ProwlarrApiError(status_code=400, message="Validation failed", details={"error": "bad_input"})

    fake.list_indexers = broken_list_indexers
    client = build_client(monkeypatch, fake)

    response = client.get("/settings/services/prowlarr/indexers")
    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["message"] == "Validation failed"
