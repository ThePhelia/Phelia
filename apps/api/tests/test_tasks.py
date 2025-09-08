from app.services.jobs import tasks
from app.services.jobs.tasks import enqueue_magnet
from app.db import models
from app.db.session import SessionLocal


def test_enqueue_magnet_not_found():
    assert enqueue_magnet(1) is False


def test_enqueue_magnet_success(monkeypatch):
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

    assert enqueue_magnet(dl_id) is True

    with SessionLocal() as db:
        d = db.get(models.Download, dl_id)
        assert d.status == "queued"
