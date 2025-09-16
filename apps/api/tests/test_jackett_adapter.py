import httpx
from typing import Dict

from app.services import jackett_adapter


def _capture_get(monkeypatch, payload):
    seen: Dict[str, object] = {}

    def fake_get(url: str, **kwargs):
        seen["url"] = url
        seen["params"] = kwargs.get("params")
        seen["headers"] = kwargs.get("headers")
        request = httpx.Request(
            "GET",
            url,
            params=kwargs.get("params"),
            headers=kwargs.get("headers"),
        )
        return httpx.Response(200, request=request, json=payload)

    monkeypatch.setattr(jackett_adapter.httpx, "get", fake_get)
    return seen


def test_fetch_indexers_uses_auth_headers(monkeypatch):
    seen = _capture_get(monkeypatch, payload=[])
    monkeypatch.setattr(jackett_adapter, "JACKETT_API_KEY", "secret")
    adapter = jackett_adapter.JackettAdapter()

    assert adapter._fetch_indexers() == []
    assert seen["params"] == {"apikey": "secret"}
    assert seen["headers"] == {"X-Api-Key": "secret"}


def test_get_schema_uses_auth_headers(monkeypatch):
    seen = _capture_get(monkeypatch, payload={"fields": []})
    monkeypatch.setattr(jackett_adapter, "JACKETT_API_KEY", "secret")
    adapter = jackett_adapter.JackettAdapter()

    assert adapter._get_schema("slug") == {"fields": []}
    assert seen["params"] == {"apikey": "secret"}
    assert seen["headers"] == {"X-Api-Key": "secret"}

