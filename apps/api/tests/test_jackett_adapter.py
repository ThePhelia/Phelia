from typing import Any, Dict

from app.services import jackett_adapter


class DummyResponse:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:  # pragma: no cover - nothing to do
        return None

    def json(self) -> Any:  # pragma: no cover - nothing to do
        return self._payload


def test_fetch_indexers_uses_api_key(monkeypatch):
    captured: Dict[str, Any] = {}

    def fake_get(url, timeout, headers=None, **kwargs):
        captured.update({"url": url, "timeout": timeout, "headers": headers, "extra": kwargs})
        return DummyResponse([])

    monkeypatch.setattr(jackett_adapter, "JACKETT_API_KEY", "secret")
    monkeypatch.setattr(jackett_adapter.httpx, "get", fake_get)

    adapter = jackett_adapter.JackettAdapter()
    assert adapter._fetch_indexers() == []
    assert captured["headers"] == {"X-Api-Key": "secret"}


def test_get_schema_uses_api_key(monkeypatch):
    captured: Dict[str, Any] = {}

    def fake_get(url, timeout, headers=None, **kwargs):
        captured.update({"url": url, "timeout": timeout, "headers": headers, "extra": kwargs})
        return DummyResponse({"fields": []})

    monkeypatch.setattr(jackett_adapter, "JACKETT_API_KEY", "another-secret")
    monkeypatch.setattr(jackett_adapter.httpx, "get", fake_get)

    adapter = jackett_adapter.JackettAdapter()
    assert adapter._get_schema("slug") == {"fields": []}
    assert captured["headers"] == {"X-Api-Key": "another-secret"}


def test_ensure_installed_uses_api_key(monkeypatch):
    captured: Dict[str, Any] = {}

    def fake_post(url, json=None, timeout=None, headers=None, **kwargs):
        captured.update({"url": url, "json": json, "timeout": timeout, "headers": headers, "extra": kwargs})
        return DummyResponse({})

    def fake_get_schema(self, slug):
        return {"fields": []}

    monkeypatch.setattr(jackett_adapter, "JACKETT_API_KEY", "post-secret")
    monkeypatch.setattr(jackett_adapter.httpx, "post", fake_post)
    monkeypatch.setattr(jackett_adapter.JackettAdapter, "_get_schema", fake_get_schema)

    adapter = jackett_adapter.JackettAdapter()
    assert adapter.ensure_installed("slug") == {"slug": "slug", "configured": True}
    assert captured["headers"] == {"X-Api-Key": "post-secret"}
