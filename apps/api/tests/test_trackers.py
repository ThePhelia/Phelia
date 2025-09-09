import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
import logging

from app.routers.trackers import router as trackers_router
from app.db import models
from app.db.session import get_db


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
                json={"name": "t2", "base_url": base_url, "api_key": "abc", "enabled": True},
            )

    assert resp.status_code == 201
    body = resp.json()
    assert "apikey" not in body["base_url"]
    assert body["base_url"].endswith("?x=1")
    assert any("stripping apikey" in r.message for r in caplog.records)
