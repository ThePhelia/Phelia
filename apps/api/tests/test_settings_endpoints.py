import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import settings as settings_router
from app.db.session import get_db
from app.plugins.loader import PluginRuntime
from app.plugins.manifest import PluginManifest


@pytest.fixture()
def plugin_runtime(tmp_path):
    manifest = PluginManifest(
        id="example.plugin",
        name="Example Plugin",
        version="1.0.0",
        entry_point="example:Plugin",
        min_phelia="0.1.0",
        description="Example",
        settings_schema={
            "properties": {
                "token": {"type": "string", "default": "abc123"},
                "enabled": {"type": "boolean", "default": True},
            },
            "required": ["token"],
        },
    )
    plugin_dir = tmp_path / "plugins" / manifest.id
    plugin_dir.mkdir(parents=True, exist_ok=True)
    site_dir = plugin_dir / "versions" / manifest.version / "site"
    site_dir.mkdir(parents=True, exist_ok=True)
    runtime = PluginRuntime(manifest=manifest, path=plugin_dir, site_dir=site_dir)
    return runtime


@pytest.mark.anyio
async def test_list_plugin_settings_returns_runtime(plugin_runtime, monkeypatch):
    monkeypatch.setattr(
        settings_router.loader, "list_plugins", lambda: [plugin_runtime]
    )

    app = FastAPI()
    app.include_router(settings_router.router, prefix="/api/v1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/settings/plugins")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["plugins"] == [
            {
                "id": plugin_runtime.manifest.id,
                "name": plugin_runtime.manifest.name,
                "contributes_settings": True,
                "settings_schema": plugin_runtime.manifest.settings_schema,
            }
        ]


@pytest.mark.anyio
async def test_plugin_settings_roundtrip(db_session, plugin_runtime, monkeypatch):
    monkeypatch.setattr(
        settings_router.loader, "list_plugins", lambda: [plugin_runtime]
    )
    monkeypatch.setattr(settings_router.loader, "get_runtime", lambda _: plugin_runtime)

    app = FastAPI()
    app.include_router(settings_router.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        initial = await client.get(
            f"/api/v1/settings/plugins/{plugin_runtime.manifest.id}"
        )
        assert initial.status_code == 200
        assert initial.json()["values"] == {
            "token": "abc123",
            "enabled": True,
        }

        update = await client.post(
            f"/api/v1/settings/plugins/{plugin_runtime.manifest.id}",
            json={"values": {"token": "updated", "enabled": False}},
        )
        assert update.status_code == 200
        assert update.json()["values"] == {"token": "updated", "enabled": False}

        reread = await client.get(
            f"/api/v1/settings/plugins/{plugin_runtime.manifest.id}"
        )
        assert reread.status_code == 200
        assert reread.json()["values"] == {"token": "updated", "enabled": False}
