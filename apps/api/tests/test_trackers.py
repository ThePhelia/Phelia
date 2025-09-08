import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

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
