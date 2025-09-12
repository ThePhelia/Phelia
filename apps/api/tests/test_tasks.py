import logging
import httpx

from app.services.jobs import tasks
from app.services.jobs.tasks import enqueue_download
from app.db import models
from app.db.session import SessionLocal


def test_enqueue_download_not_found(caplog):
    with caplog.at_level(logging.WARNING, logger=tasks.logger.name):
        assert enqueue_download(1) is False
    assert any("not found" in r.message for r in caplog.records)


def test_enqueue_download_missing_source(caplog):
    with SessionLocal() as db:
        dl = models.Download(magnet="", save_path="/downloads", status="queued")
        db.add(dl)
        db.commit()
        db.refresh(dl)
        dl_id = dl.id

    with caplog.at_level(logging.WARNING, logger=tasks.logger.name):
        assert enqueue_download(dl_id) is False
    assert any("missing magnet or url" in r.message for r in caplog.records)


def test_enqueue_download_magnet_success(monkeypatch):
    class FakeQB:
        def login(self):
            pass
        def add_magnet(self, magnet, save_path):
            pass
        def list_torrents(self):
            return []
    monkeypatch.setattr(tasks, "_qb", lambda: FakeQB())

    with SessionLocal() as db:
        dl = models.Download(magnet="magnet:?xt=urn:btih:abcd", save_path="/downloads", status="queued")
        db.add(dl)
        db.commit()
        db.refresh(dl)
        dl_id = dl.id

    assert enqueue_download(dl_id) is True

    with SessionLocal() as db:
        d = db.get(models.Download, dl_id)
        assert d.status == "queued"


def test_enqueue_download_url_success(monkeypatch):
    class FakeQB:
        def login(self):
            pass
        def add_torrent_file(self, torrent, save_path):
            pass
        def list_torrents(self):
            return []

    monkeypatch.setattr(tasks, "_qb", lambda: FakeQB())

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def get(self, url, follow_redirects=True):
            return type(
                "R",
                (),
                {"content": b"data", "raise_for_status": lambda self: None},
            )()

    monkeypatch.setattr(tasks.httpx, "AsyncClient", lambda: FakeAsyncClient())

    with SessionLocal() as db:
        dl = models.Download(magnet="", save_path="/downloads", status="queued")
        db.add(dl)
        db.commit()
        db.refresh(dl)
        dl_id = dl.id

    assert enqueue_download(dl_id, url="http://example.com/file.torrent") is True

    with SessionLocal() as db:
        d = db.get(models.Download, dl_id)
        assert d.status == "queued"


def test_enqueue_download_url_magnet(monkeypatch):
    class FakeQB:
        def __init__(self):
            self.magnet = None

        def login(self):
            pass

        def add_magnet(self, magnet, save_path):
            self.magnet = magnet

        def list_torrents(self):
            return []

    qb = FakeQB()
    monkeypatch.setattr(tasks, "_qb", lambda: qb)

    class BadAsyncClient:
        async def __aenter__(self):
            raise AssertionError("HTTP request should not be made")

        async def __aexit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(tasks.httpx, "AsyncClient", lambda: BadAsyncClient())

    with SessionLocal() as db:
        dl = models.Download(magnet="", save_path="/downloads", status="queued")
        db.add(dl)
        db.commit()
        db.refresh(dl)
        dl_id = dl.id

    magnet_uri = "magnet:?xt=urn:btih:abcd"
    assert enqueue_download(dl_id, url=magnet_uri) is True
    assert qb.magnet == magnet_uri

    with SessionLocal() as db:
        d = db.get(models.Download, dl_id)
        assert d.magnet == magnet_uri
<<<<<<< ours
=======
        assert d.status == "queued"
>>>>>>> theirs


def test_safe_list_torrents_logs(monkeypatch, caplog):
    class BadQB:
        def list_torrents(self):
            raise RuntimeError("fail")

    with caplog.at_level(logging.WARNING, logger=tasks.logger.name):
        assert tasks._safe_list_torrents(BadQB()) == []
    assert any("Failed to list torrents" in r.message for r in caplog.records)


<<<<<<< ours
def test_poll_status_handles_http_error(monkeypatch, caplog):
    class BadQB:
        def login(self):
            raise httpx.HTTPError("boom")

    # ensure _qb returns our failing client
    monkeypatch.setattr(tasks, "_qb", lambda: BadQB())

    with SessionLocal() as db:
        dl = models.Download(magnet="m", save_path="/downloads", status="queued")
        db.add(dl)
        db.commit()

    with caplog.at_level(logging.WARNING, logger=tasks.logger.name):
        assert tasks.poll_status() == 0
    assert any("HTTP error talking to qBittorrent" in r.message for r in caplog.records)
=======
def test_pick_candidate_prefers_hash():
    stats = [
        {"hash": "AAA111", "name": "dl1", "save_path": "/downloads"},
        {"hash": "BBB222", "name": "other", "save_path": "/downloads"},
    ]
    d = models.Download(
        hash="bbb222", name="dl1", magnet="m", save_path="/downloads", status="queued"
    )
    cand = tasks._pick_candidate(stats, d)
    assert cand["hash"].lower() == "bbb222"
>>>>>>> theirs
