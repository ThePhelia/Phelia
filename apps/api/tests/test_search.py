import feedparser
import logging
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.routers.search import router as search_router, logger as search_logger
from app.services.search.torznab import TorznabClient
from app.db import models
from app.db.session import get_db


@pytest.mark.anyio
async def test_search_error_logs(monkeypatch, db_session, caplog):
    tr = models.Tracker(
        provider_slug="t1",
        display_name="t1",
        type="public",
        enabled=True,
        torznab_url="http://example",
        requires_auth=False,
    )
    db_session.add(tr)
    db_session.commit()

    def bad_search(self, base_url, query):
        raise RuntimeError("boom")

    monkeypatch.setattr(TorznabClient, "search", bad_search)

    app = FastAPI()
    app.include_router(search_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    with caplog.at_level(logging.WARNING, logger=search_logger.name):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/search", params={"query": "foo"})
    assert resp.status_code == 200
    assert any("Error searching tracker" in r.message for r in caplog.records)


@pytest.mark.anyio
async def test_search_no_trackers_returns_400(db_session):
    app = FastAPI()
    app.include_router(search_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/search", params={"query": "foo"})

    assert resp.status_code == 400
    assert resp.json()["detail"] == "No torznab trackers configured"


def test_torznab_client_builds_url(monkeypatch):
    captured = {}

    def fake_parse(url):
        captured["url"] = url

        class Feed:
            entries = []

        return Feed()

    monkeypatch.setattr(feedparser, "parse", fake_parse)
    client = TorznabClient()
    items = client.search("http://example/", "foo bar")

    assert items == []
    assert captured["url"] == "http://example?t=search&q=foo+bar"
