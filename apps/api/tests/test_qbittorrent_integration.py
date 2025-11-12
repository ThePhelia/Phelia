import os
import shutil
import subprocess
import time
import asyncio
from pathlib import Path

import pytest
import httpx

from app.services.bt.qbittorrent import QbClient
from app.services.jobs.tasks import enqueue_download, poll_status
from app.db import models

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def qbittorrent_container(tmp_path_factory):
    """Start a qBittorrent container for tests."""
    if shutil.which("docker") is None:
        pytest.skip("docker not available")
    downloads = tmp_path_factory.mktemp("qb-dl")
    cmd = [
        "docker",
        "run",
        "-d",
        "-p",
        "8080:8080",
        "-p",
        "8999:8999",
        "-e",
        "WEBUI_PORT=8080",
        "-e",
        "PUID=0",
        "-e",
        "PGID=0",
        "-v",
        f"{downloads}:/downloads",
        "lscr.io/linuxserver/qbittorrent:latest",
    ]
    cid = subprocess.check_output(cmd).decode().strip()
    # wait for API
    url = "http://localhost:8080/api/v2/app/version"
    for _ in range(30):
        try:
            r = httpx.get(url)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        subprocess.run(["docker", "logs", cid], check=False)
        subprocess.run(["docker", "rm", "-f", cid], check=False)
        raise RuntimeError("qBittorrent failed to start")
    yield downloads
    subprocess.run(["docker", "rm", "-f", cid], check=False)


@pytest.fixture
def qbittorrent(qbittorrent_container):
    downloads = qbittorrent_container
    client = QbClient(
        os.environ["QB_URL"], os.environ["QB_USER"], os.environ["QB_PASS"]
    )
    asyncio.run(client.login())
    try:
        yield client, downloads
    finally:
        # remove all torrents and close client
        try:
            torrents = asyncio.run(client.list_torrents())
            for t in torrents:
                asyncio.run(client.delete_torrent(t["hash"], True))
        finally:
            asyncio.run(client.close())


@pytest.mark.anyio
async def test_magnet_download_status(qbittorrent, db_session):
    qb, _ = qbittorrent
    magnet = "magnet:?xt=urn:btih:AB859E6F6246FFBE0BFD8D25E1502058E8CCFFB8"
    dl = models.Download(magnet=magnet, save_path="/downloads", status="queued")
    db_session.add(dl)
    db_session.commit()
    assert enqueue_download(dl.id) is True
    poll_status()
    db_session.refresh(dl)
    assert dl.status in {"metaDL", "downloading"}


@pytest.mark.anyio
async def test_file_download_status(qbittorrent, db_session, monkeypatch):
    qb, downloads = qbittorrent
    # ensure file exists so torrent completes immediately
    shutil.copy(DATA_DIR / "testfile.txt", downloads / "testfile.txt")
    torrent_bytes = (DATA_DIR / "testfile.torrent").read_bytes()

    class DummyAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _tb):
            return False

        async def get(self, url, _follow_redirects=False):
            return httpx.Response(200, content=torrent_bytes)

    monkeypatch.setattr(
        httpx, "AsyncClient", lambda *_args, **_kwargs: DummyAsyncClient()
    )

    dl = models.Download(magnet="", save_path="/downloads", status="queued")
    db_session.add(dl)
    db_session.commit()
    assert enqueue_download(dl.id, url="http://example.com/test.torrent") is True
    poll_status()
    db_session.refresh(dl)
    assert dl.status in {"pausedUP", "stalledUP", "uploading", "completed"}
