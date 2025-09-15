import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.routers.trackers import router as trackers_router
from app.db.session import get_db
from app.services import jackett_adapter


class FakeAdapter:
    def __init__(self):
        self.enabled: dict[str, bool] = {}

    def list_configured(self):
        return []

    def list_available(self):
        return [
            {
                "slug": "rutracker",
                "name": "RuTracker",
                "type": "private",
                "needs": ["username", "password"],
            }
        ]

    def ensure_installed(self, slug, creds):
        if not creds:
            raise ValueError('missing_credentials:["username", "password"]')
        assert creds == {"username": "u", "password": "p"}
        return {
            "slug": slug,
            "name": "RuTracker",
            "type": "private",
            "needs": ["username", "password"],
        }

    def get_torznab_url(self, slug):
        return f"http://jackett/{slug}/"

    def fetch_caps(self, url):
        return {"foo": "bar"}

    def test_search(self, url, q="test"):
        return True, 123

    def enable(self, slug, enabled):
        self.enabled[slug] = enabled

    def remove(self, slug):
        self.enabled.pop(slug, None)


@pytest.mark.anyio
async def test_connect_toggle_and_test(db_session, monkeypatch):
    # Patch adapter
    monkeypatch.setattr(jackett_adapter, "JackettAdapter", FakeAdapter)
    from app.routers import trackers as trackers_module
    monkeypatch.setattr(trackers_module, "JackettAdapter", FakeAdapter)

    app = FastAPI()
    app.include_router(trackers_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Missing credentials
        resp = await ac.post("/api/v1/trackers/providers/rutracker/connect", json={})
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "missing_credentials"

        # Connect with credentials
        resp = await ac.post(
            "/api/v1/trackers/providers/rutracker/connect",
            json={"username": "u", "password": "p"},
        )
        assert resp.status_code == 200
        tid = resp.json()["tracker"]["id"]

        # Toggle
        resp = await ac.post(f"/api/v1/trackers/{tid}/toggle", json={"enabled": False})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

        # Test
        resp = await ac.post(f"/api/v1/trackers/{tid}/test")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Delete
        resp = await ac.delete(f"/api/v1/trackers/{tid}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


def test_jackett_adapter_raises_on_redirect(monkeypatch):
    adapter = jackett_adapter.JackettAdapter()

    seen_kwargs: dict[str, object] = {}

    def fake_get(url: str, **kwargs):
        seen_kwargs.update(kwargs)
        request = httpx.Request("GET", url, params=kwargs.get("params"))
        return httpx.Response(
            302,
            headers={"Location": "http://jackett/redirect"},
            request=request,
        )

    monkeypatch.setattr(jackett_adapter.httpx, "get", fake_get)

    with pytest.raises(RuntimeError) as exc:
        adapter.fetch_caps("slug")

    assert "redirect" in str(exc.value)
    assert seen_kwargs.get("follow_redirects") is True
