import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
import logging
import base64
from typing import Any

from app.routers.trackers import router as trackers_router
from app.db import models
from app.db.session import get_db
import httpx


@pytest.mark.anyio
async def test_update_tracker_lookup(db_session):
    tr = models.Tracker(name="t1", type="torznab", base_url="http://example", creds_enc="", enabled=True)
    db_session.add(tr)
    db_session.commit()
    db_session.refresh(tr)

    app = FastAPI()
    app.include_router(trackers_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_ok = await ac.patch(f"/api/v1/trackers/{tr.id}", json={"name": "updated"})
        resp_notfound = await ac.patch(f"/api/v1/trackers/{tr.id + 1}", json={"name": "updated"})

    assert resp_ok.status_code == 200
    assert resp_ok.json()["name"] == "updated"
    assert resp_notfound.status_code == 404


@pytest.mark.anyio
async def test_create_tracker_strips_apikey(db_session, caplog):
    app = FastAPI()
    app.include_router(trackers_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    base_url = "http://example?apikey=abc&x=1"
    with caplog.at_level(logging.WARNING):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/trackers",
                json={
                    "name": "t2",
                    "base_url": base_url,
                    "api_key": "abc",
                    "username": "user1",
                    "password": "pass1",
                    "enabled": True,
                },
            )

    assert resp.status_code == 201
    body = resp.json()
    assert "apikey" not in body["base_url"]
    assert body["base_url"].endswith("?x=1")
    assert any("stripping apikey" in r.message for r in caplog.records)
    tr = db_session.query(models.Tracker).filter(models.Tracker.id == body["id"]).first()
    assert tr.username == "user1"
    assert tr.password_enc and tr.password_enc != "pass1"


@pytest.mark.anyio
async def test_create_tracker_jackett(db_session, monkeypatch):
    app = FastAPI()
    app.include_router(trackers_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    monkeypatch.setattr("app.routers.trackers.read_jackett_apikey", lambda: "sekret")

    captured: dict[str, Any] = {}

    class FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return {
                "id": "foo",
                "apiKey": "sekret",
                "baseUrl": "http://jackett:9117/api/v2.0/indexers/foo/results/torznab/",
            }

        def raise_for_status(self):
            return None

    def fake_post(url, params=None, json=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["json"] = json
        return FakeResp()

    monkeypatch.setattr(httpx, "post", fake_post)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/trackers",
            json={"name": "n1", "jackett_id": "foo", "username": "u", "password": "p"},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["base_url"] == "http://jackett:9117/api/v2.0/indexers/foo/results/torznab/"
    assert captured["url"].endswith("/api/v2.0/indexers/foo")
    assert captured["json"]["config"]["username"] == "u"


@pytest.mark.anyio
async def test_test_tracker_uses_basic_auth(monkeypatch, db_session):
    enc = base64.b64encode(b"pw").decode()
    tr = models.Tracker(
        name="t1",
        type="torznab",
        base_url="http://example",
        creds_enc="{}",
        username="user",
        password_enc=enc,
        enabled=True,
    )
    db_session.add(tr)
    db_session.commit()
    db_session.refresh(tr)

    app = FastAPI()
    app.include_router(trackers_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    captured = {}

    class MockResp:
        status_code = 200
        text = "<caps></caps>"
        content = b"<caps></caps>"

    async def fake_get(self, url, auth=None, **kwargs):
        captured["url"] = url
        captured["auth"] = auth
        return MockResp()

    monkeypatch.setattr(AsyncClient, "get", fake_get)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(f"/api/v1/trackers/{tr.id}/test")

    assert resp.status_code == 200
    assert captured["auth"] == ("user", "pw")


@pytest.mark.anyio
async def test_jackett_default(db_session, monkeypatch):
    app = FastAPI()
    app.include_router(trackers_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    monkeypatch.setattr("app.routers.trackers.read_jackett_apikey", lambda: "sekret")

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/trackers/jackett/default")

    assert resp.status_code == 200
    assert resp.json()["api_key"] == "sekret"
