import pytest
import httpx
from urllib.parse import parse_qsl

from app.services.bt.qbittorrent import QbClient


@pytest.mark.anyio
async def test_pause_torrent_posts_hash():
    recorded = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        recorded["url"] = str(request.url)
        recorded["data"] = dict(parse_qsl(request.content.decode()))
        return httpx.Response(200, json={})

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
        return httpx.Response(200, json={})

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
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    client = None
    async with QbClient("http://qb", "user", "pass") as qb:
        qb._client = httpx.AsyncClient(transport=transport)
        client = qb._client
        await qb.delete_torrent("abc", True)

    assert recorded["url"] == "http://qb/api/v2/torrents/delete"
    assert recorded["data"] == {"hashes": "abc", "deleteFiles": "true"}
    assert client.is_closed
