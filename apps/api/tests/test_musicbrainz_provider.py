from __future__ import annotations

import importlib

import pytest

import phelia.discovery.providers.musicbrainz as musicbrainz_module


@pytest.mark.anyio
async def test_musicbrainz_provider_uses_metadata_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("METADATA_BASE_URL", "http://metadata-proxy:8080")
    monkeypatch.setenv("MB_USER_AGENT", "TestAgent/1.0")

    module = importlib.reload(musicbrainz_module)

    calls: dict[str, object] = {}

    class DummyResponse:
        status_code = 200
        headers: dict[str, str] = {}

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"release-groups": []}

    class DummyAsyncClient:
        def __init__(
            self, *args, **kwargs
        ) -> None:  # noqa: D401 - mimic httpx.AsyncClient
            calls["headers"] = kwargs.get("headers")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str, params=None):
            calls["url"] = url
            calls["params"] = params
            return DummyResponse()

    monkeypatch.setattr(module.httpx, "AsyncClient", DummyAsyncClient)

    provider = module.MusicBrainzProvider()
    await provider.search_albums(query="Test", limit=1)

    assert calls["url"] == "http://metadata-proxy:8080/mb/release-group"
    assert isinstance(calls["params"], dict)
    assert calls["params"]["fmt"] == "json"
