from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import settings as settings_endpoints


class Snapshot:
    def __init__(self, url: str, api_key: str | None):
        self.url = url
        self.api_key = api_key


def test_update_prowlarr_settings(monkeypatch):
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
        "/settings/services/prowlarr",
        json={"url": "http://prowlarr.local", "api_key": "key12345"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "url": "http://prowlarr.local",
        "api_key_configured": True,
    }


def test_update_prowlarr_settings_rejects_invalid_url():
    app = FastAPI()
    app.include_router(settings_endpoints.router, prefix="")

    client = TestClient(app)
    response = client.post(
        "/settings/services/prowlarr",
        json={"url": "notaurl"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == {
        "error": "validation_failed",
        "field": "url",
        "message": "url must be a valid http(s) URL",
    }


def test_discover_prowlarr_api_key_success(monkeypatch):
    app = FastAPI()
    app.include_router(settings_endpoints.router, prefix="")

    monkeypatch.setattr(
        settings_endpoints.runtime_service_settings,
        "prowlarr_snapshot",
        lambda: Snapshot(url="http://prowlarr.local:9696", api_key=None),
    )
    monkeypatch.setattr(
        settings_endpoints,
        "_discover_prowlarr_api_key",
        lambda force_refresh=False, auth=None: ("abcd1234", False),
    )

    client = TestClient(app)
    response = client.post("/settings/services/prowlarr/discover-api-key", json={})

    assert response.status_code == 200
    assert response.json() == {
        "connected": True,
        "api_key_configured": True,
        "status": "success",
        "message": "Fetched and saved API key from Prowlarr.",
    }


def test_discover_prowlarr_api_key_failure_includes_manual_hint(monkeypatch):
    app = FastAPI()
    app.include_router(settings_endpoints.router, prefix="")

    monkeypatch.setattr(
        settings_endpoints.runtime_service_settings,
        "prowlarr_snapshot",
        lambda: Snapshot(url="http://prowlarr.local:9696", api_key=None),
    )
    monkeypatch.setattr(
        settings_endpoints,
        "_discover_prowlarr_api_key",
        lambda force_refresh=False, auth=None: (None, False),
    )

    client = TestClient(app)
    response = client.post("/settings/services/prowlarr/discover-api-key", json={})

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "prowlarr_api_key_discovery_failed"
    assert "manual_entry_hint" in response.json()["detail"]


def test_get_services_autoloads_api_key_when_missing(monkeypatch):
    app = FastAPI()
    app.include_router(settings_endpoints.router, prefix="")

    monkeypatch.setattr(settings_endpoints, "_autoload_prowlarr_api_key", lambda: None)
    monkeypatch.setattr(
        settings_endpoints.runtime_service_settings,
        "prowlarr_snapshot",
        lambda: Snapshot(url="http://prowlarr.local:9696", api_key="fetched-key"),
    )

    class QbSnapshot:
        url = "http://qbittorrent:8080"
        username = "admin"
        password = None

    class DownloadSnapshot:
        allowed_dirs = ["/downloads"]
        default_dir = "/downloads"

    monkeypatch.setattr(settings_endpoints.runtime_service_settings, "qbittorrent_snapshot", lambda: QbSnapshot())
    monkeypatch.setattr(settings_endpoints.runtime_service_settings, "download_snapshot", lambda: DownloadSnapshot())

    client = TestClient(app)
    response = client.get("/settings/services")

    assert response.status_code == 200
    assert response.json()["prowlarr"] == {
        "url": "http://prowlarr.local:9696",
        "api_key_configured": True,
    }


def test_discover_prowlarr_api_key_reads_from_volume_when_http_unavailable(monkeypatch, tmp_path):
    app = FastAPI()
    app.include_router(settings_endpoints.router, prefix="")

    state = {"url": "http://prowlarr:9696", "api_key": None}

    def prowlarr_snapshot():
        return Snapshot(url=state["url"], api_key=state["api_key"])

    def update_prowlarr(*, url=None, api_key=None):
        if url is not None:
            state["url"] = url
        if api_key is not None:
            state["api_key"] = api_key
        return True

    config_xml = tmp_path / "config.xml"
    config_xml.write_text("<Config><ApiKey>abc123xyz</ApiKey></Config>")

    monkeypatch.setattr(settings_endpoints.runtime_service_settings, "prowlarr_snapshot", prowlarr_snapshot)
    monkeypatch.setattr(settings_endpoints.runtime_service_settings, "update_prowlarr", update_prowlarr)
    monkeypatch.setattr(settings_endpoints, "_refresh_prowlarr_provider", lambda: None)
    monkeypatch.setattr(settings_endpoints, "_PROWLARR_CONFIG_XML_PATHS", (config_xml,))

    def raise_http_error(*_args, **_kwargs):
        raise httpx.ConnectError("unavailable")

    monkeypatch.setattr(settings_endpoints.httpx, "get", raise_http_error)

    client = TestClient(app)
    response = client.post("/settings/services/prowlarr/discover-api-key", json={})

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert state["api_key"] == "abc123xyz"


def test_discover_prowlarr_api_key_failure_when_http_and_volume_missing(monkeypatch, tmp_path):
    app = FastAPI()
    app.include_router(settings_endpoints.router, prefix="")

    missing_path = tmp_path / "missing.xml"

    monkeypatch.setattr(
        settings_endpoints.runtime_service_settings,
        "prowlarr_snapshot",
        lambda: Snapshot(url="http://prowlarr.local:9696", api_key=None),
    )
    monkeypatch.setattr(settings_endpoints, "_PROWLARR_CONFIG_XML_PATHS", (Path(missing_path),))

    def raise_http_error(*_args, **_kwargs):
        raise httpx.ConnectError("unavailable")

    monkeypatch.setattr(settings_endpoints.httpx, "get", raise_http_error)

    client = TestClient(app)
    response = client.post("/settings/services/prowlarr/discover-api-key", json={})

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "prowlarr_api_key_discovery_failed"
    assert "manual_entry_hint" in response.json()["detail"]
