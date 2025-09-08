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
    qb = QbClient("http://qb", "user", "pass")
    qb._client = httpx.AsyncClient(transport=transport)
    await qb.pause_torrent("abc")
    await qb._client.aclose()

    assert recorded["url"] == "http://qb/api/v2/torrents/pause"
    assert recorded["data"] == {"hashes": "abc"}


@pytest.mark.anyio
async def test_resume_torrent_posts_hash():
    recorded = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        recorded["url"] = str(request.url)
        recorded["data"] = dict(parse_qsl(request.content.decode()))
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    qb = QbClient("http://qb", "user", "pass")
    qb._client = httpx.AsyncClient(transport=transport)
    await qb.resume_torrent("abc")
    await qb._client.aclose()

    assert recorded["url"] == "http://qb/api/v2/torrents/resume"
    assert recorded["data"] == {"hashes": "abc"}


@pytest.mark.anyio
async def test_delete_torrent_posts_hash_and_flag():
    recorded = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        recorded["url"] = str(request.url)
        recorded["data"] = dict(parse_qsl(request.content.decode()))
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    qb = QbClient("http://qb", "user", "pass")
    qb._client = httpx.AsyncClient(transport=transport)
    await qb.delete_torrent("abc", True)
    await qb._client.aclose()

    assert recorded["url"] == "http://qb/api/v2/torrents/delete"
    assert recorded["data"] == {"hashes": "abc", "deleteFiles": "true"}
