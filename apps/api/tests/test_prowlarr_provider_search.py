import pytest
import httpx

from app.services.prowlarr_client import ProwlarrApiError
from app.services.search.prowlarr.provider import ProwlarrProvider
from app.services.search.prowlarr.settings import ProwlarrSettings


class _DummyAsyncClient:
    def __init__(self, *, response: httpx.Response):
        self._response = response
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        self.calls.append((url, params or {}))
        request = httpx.Request("GET", url, params=params)
        self._response._request = request
        return self._response


@pytest.mark.anyio
async def test_provider_uses_v1_search_endpoint_and_normalizes(monkeypatch):
    response = httpx.Response(
        status_code=200,
        json=[
            {
                "title": "Example Release",
                "guid": "abc",
                "size": 1234,
                "seeders": 55,
                "leechers": 9,
                "categories": ["Movies"],
                "magnetUrl": "magnet:?xt=urn:btih:abc",
                "downloadUrl": "https://indexer.test/torrent",
                "indexer": "IndexerA",
            }
        ],
    )
    fake_client = _DummyAsyncClient(response=response)

    def _client_factory(*args, **kwargs):
        return fake_client

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory)

    settings = ProwlarrSettings(
        prowlarr_url="http://localhost:9696",
        prowlarr_api_key="secret-key",
        qbittorrent_url="http://qbittorrent:8080",
    )
    provider = ProwlarrProvider(settings)

    cards, _ = await provider.search("test", limit=10, kind="all")

    assert len(cards) == 1
    source = cards[0].details["prowlarr"]
    assert source["tracker"] == "IndexerA"
    assert source["seeders"] == 55
    assert source["peers"] == 9
    assert source["magnet"] == "magnet:?xt=urn:btih:abc"
    assert source["torrentUrl"] == "https://indexer.test/torrent"

    called_url, called_params = fake_client.calls[0]
    assert called_url.endswith("/api/v1/search")
    assert "torznab/api" not in called_url
    assert called_params["query"] == "test"
    assert called_params["type"] == "search"
    assert called_params["apikey"] == "secret-key"


@pytest.mark.anyio
async def test_provider_maps_http_error_to_prowlarr_api_error(monkeypatch):
    response = httpx.Response(status_code=404, text="not found")
    fake_client = _DummyAsyncClient(response=response)

    def _client_factory(*args, **kwargs):
        return fake_client

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory)

    settings = ProwlarrSettings(
        prowlarr_url="http://localhost:9696",
        prowlarr_api_key="secret-key",
        qbittorrent_url="http://qbittorrent:8080",
    )
    provider = ProwlarrProvider(settings)

    with pytest.raises(ProwlarrApiError) as excinfo:
        await provider.search("test", limit=10, kind="all")

    assert excinfo.value.status_code == 404
    assert isinstance(excinfo.value.details, dict)
    assert excinfo.value.details["status"] == 404
