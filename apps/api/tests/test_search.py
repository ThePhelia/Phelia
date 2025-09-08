import json
import logging
import pytest
import feedparser
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.routers.search import router as search_router, logger as search_logger
from app.services.search.torznab import TorznabClient
from app.db import models
from app.db.session import get_db


@pytest.mark.anyio
async def test_search_missing_api_key_logs(db_session, caplog):
    tr = models.Tracker(name="t1", type="torznab", base_url="http://example", creds_enc="{}", enabled=True)
    db_session.add(tr)
    db_session.commit()

    app = FastAPI()
    app.include_router(search_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    with caplog.at_level(logging.WARNING, logger=search_logger.name):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/v1/search", params={"query": "foo"})
    assert resp.status_code == 200
    assert any("missing api_key" in r.message for r in caplog.records)


@pytest.mark.anyio
async def test_search_error_logs(monkeypatch, db_session, caplog):
    creds = json.dumps({"api_key": "123"})
    tr = models.Tracker(name="t1", type="torznab", base_url="http://example", creds_enc=creds, enabled=True)
    db_session.add(tr)
    db_session.commit()

    def bad_search(self, base_url, api_key, query):
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


def test_torznab_client_builds_url(monkeypatch):
    captured = {}

    def fake_parse(url):
        captured["url"] = url

        class Feed:
            entries = []

        return Feed()

    monkeypatch.setattr(feedparser, "parse", fake_parse)
    client = TorznabClient()
    items = client.search("http://example/", "secret", "foo bar")

    assert items == []
    assert (
        captured["url"]
        == "http://example?t=search&q=foo+bar&apikey=secret"
    )
