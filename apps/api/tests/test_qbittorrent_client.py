import pytest
import httpx
from urllib.parse import parse_qsl

from app.services.bt.qbittorrent import QbClient


@pytest.mark.anyio
async def test_list_torrents_returns_json():
    recorded = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        recorded["url"] = str(request.url)
        recorded["headers"] = dict(request.headers)
        return httpx.Response(200, json=[{"name": "a"}])

    transport = httpx.MockTransport(handler)
    client = None
    async with QbClient("http://qb", "user", "pass") as qb:
        qb._client = httpx.AsyncClient(transport=transport)
        client = qb._client
        items = await qb.list_torrents()

    assert recorded["url"] == "http://qb/api/v2/torrents/info"
    assert recorded["headers"]["referer"] == "http://qb/"
    assert items == [{"name": "a"}]
    assert client.is_closed


@pytest.mark.anyio
async def test_pause_torrent_posts_hash():
    recorded = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        recorded["url"] = str(request.url)
        recorded["data"] = dict(parse_qsl(request.content.decode()))
        return httpx.Response(200, text="Ok.")

    transport = httpx.MockTransport(handler)
    client = None
    async with QbClient("http://qb", "user", "pass") as qb:
        qb._client = httpx.AsyncClient(transport=transport)
        client = qb._client
        await qb.pause_torrent("abc")

    assert recorded["url"] == "http://qb/api/v2/torrents/pause"
    assert recorded["data"] == {"hashes": "abc"}
    assert client.is_closed


@pytest.mark.anyio
async def test_resume_torrent_posts_hash():
    recorded = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        recorded["url"] = str(request.url)
        recorded["data"] = dict(parse_qsl(request.content.decode()))
        return httpx.Response(200, text="Ok.")

    transport = httpx.MockTransport(handler)
    client = None
    async with QbClient("http://qb", "user", "pass") as qb:
        qb._client = httpx.AsyncClient(transport=transport)
        client = qb._client
        await qb.resume_torrent("abc")

    assert recorded["url"] == "http://qb/api/v2/torrents/resume"
    assert recorded["data"] == {"hashes": "abc"}
    assert client.is_closed


@pytest.mark.anyio
async def test_delete_torrent_posts_hash_and_flag():
    recorded = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        recorded["url"] = str(request.url)
        recorded["data"] = dict(parse_qsl(request.content.decode()))
        return httpx.Response(200, text="Ok.")

    transport = httpx.MockTransport(handler)
    client = None
    async with QbClient("http://qb", "user", "pass") as qb:
        qb._client = httpx.AsyncClient(transport=transport)
        client = qb._client
        await qb.delete_torrent("abc", True)

    assert recorded["url"] == "http://qb/api/v2/torrents/delete"
    assert recorded["data"] == {"hashes": "abc", "deleteFiles": "true"}
    assert client.is_closed


@pytest.mark.anyio
async def test_delete_torrent_allows_blank_response():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="")

    transport = httpx.MockTransport(handler)

    async with QbClient("http://qb", "user", "pass") as qb:
        qb._client = httpx.AsyncClient(transport=transport)
        await qb.delete_torrent("abc", False)


@pytest.mark.anyio
async def test_post_requests_include_referer(monkeypatch):
    recorded = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.headers.get("referer") != "http://qb/":
            return httpx.Response(403)
        recorded["headers"] = dict(request.headers)
        return httpx.Response(200, text="Ok.")

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*_args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*_args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    async with QbClient("http://qb", "user", "pass") as qb:
        await qb.add_magnet("magnet:?xt=urn:btih:abc")

    assert recorded["headers"]["referer"] == "http://qb/"


@pytest.mark.anyio
async def test_add_torrent_file_includes_referer(monkeypatch):
    recorded = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.headers.get("referer") != "http://qb/":
            return httpx.Response(403)
        recorded["headers"] = dict(request.headers)
        return httpx.Response(200, text="Ok.")

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*_args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*_args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    async with QbClient("http://qb", "user", "pass") as qb:
        await qb.add_torrent_file(b"data")

    assert recorded["headers"]["referer"] == "http://qb/"


@pytest.mark.anyio
async def test_add_magnet_allows_blank_response():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="")

    transport = httpx.MockTransport(handler)

    async with QbClient("http://qb", "user", "pass") as qb:
        qb._client = httpx.AsyncClient(transport=transport)
        await qb.add_magnet("magnet:?xt=urn:btih:abc")
