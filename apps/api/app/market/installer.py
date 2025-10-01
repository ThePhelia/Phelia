from __future__ import annotations

import json
import shutil
import subprocess
import sys
from typing import Any

import httpx

from app.plugins.loader import (
    disable_plugin,
    import_entry,
    plugin_root_dir,
    plugin_site_dir,
    register_plugin,
    remove_plugin,
)
from app.plugins.manifest import PluginManifest

from .registry import PluginIndexItem, verify_sha256


async def download(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=60.0)
        response.raise_for_status()
        return response.content


async def install(item: PluginIndexItem) -> dict[str, Any]:
    artifact_bytes = await download(item.artifact.url)
    verify_sha256(artifact_bytes, item.artifact.sha256)

    plugin_dir = plugin_root_dir(item.id)
    if plugin_dir.exists():
        shutil.rmtree(plugin_dir)
    plugin_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = plugin_dir / "artifact.whl"
    with artifact_path.open("wb") as fh:
        fh.write(artifact_bytes)

    site_dir = plugin_site_dir(item.id)
    site_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--upgrade",
            "-t",
            str(site_dir),
            str(artifact_path),
        ],
        check=True,
    )

    manifest = PluginManifest(
        id=item.id,
        name=item.name,
        version=item.version,
        description=item.description,
        entry_point=item.entry_point,
        permissions=item.permissions,
        settings_schema=item.settings_schema,
        routes=item.routes,
        contributes_settings=item.contributes_settings,
    )

    manifest_path = plugin_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest.model_dump(), fh, indent=2)

    instance = import_entry(site_dir, manifest.entry_point)
    register_plugin(manifest, instance)

    return {"id": item.id, "version": item.version}


def uninstall(plugin_id: str) -> None:
    try:
        disable_plugin(plugin_id, {})
    except KeyError:
        pass

    remove_plugin(plugin_id)

    plugin_dir = plugin_root_dir(plugin_id)
    if plugin_dir.exists():
        shutil.rmtree(plugin_dir)

