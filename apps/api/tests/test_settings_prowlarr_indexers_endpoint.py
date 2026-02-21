from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import settings as settings_endpoints
from app.services.prowlarr_client import ProwlarrApiError


class FakeClient:
    def __init__(self):
        self.calls: list[tuple[str, object]] = []
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
        self.calls.append(("list_indexers", None))
        return self.indexers

    async def list_indexer_templates(self):
        self.calls.append(("list_indexer_templates", None))
        return self.templates

    async def create_indexer(self, payload):
        self.calls.append(("create_indexer", payload))
        return {**payload, "id": 99, "enable": True, "fields": payload.get("fields", [])}

    async def update_indexer(self, indexer_id, payload):
        self.calls.append(("update_indexer", {"id": indexer_id, "payload": payload}))
        return {**payload, "id": indexer_id}

    async def delete_indexer(self, indexer_id):
        self.calls.append(("delete_indexer", indexer_id))
        return None

    async def test_indexer(self, payload):
        self.calls.append(("test_indexer", payload))
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
    fake = FakeClient()
    client = build_client(monkeypatch, fake)
    response = client.post(
        "/settings/services/prowlarr/indexers",
        json={"template_id": 10, "name": "New Indexer", "settings": {"baseUrl": "https://new.example"}},
    )
    assert response.status_code == 200
    assert response.json()["id"] == 99
    assert fake.calls[0][0] == "list_indexer_templates"
    assert fake.calls[1][0] == "create_indexer"


def test_update_indexer_proxies_payload(monkeypatch):
    fake = FakeClient()
    client = build_client(monkeypatch, fake)
    response = client.put(
        "/settings/services/prowlarr/indexers/1",
        json={"name": "Updated", "settings": {"baseUrl": "https://updated.example"}},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated"
    assert fake.calls[0][0] == "list_indexers"
    assert fake.calls[1][0] == "update_indexer"


def test_delete_indexer_proxies_to_prowlarr(monkeypatch):
    fake = FakeClient()
    client = build_client(monkeypatch, fake)

    response = client.delete("/settings/services/prowlarr/indexers/1")

    assert response.status_code == 204
    assert ("delete_indexer", 1) in fake.calls


def test_test_indexer_proxies_to_prowlarr(monkeypatch):
    fake = FakeClient()
    client = build_client(monkeypatch, fake)

    response = client.post("/settings/services/prowlarr/indexers/1/test")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert fake.calls[0][0] == "list_indexers"
    assert fake.calls[1][0] == "test_indexer"


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
