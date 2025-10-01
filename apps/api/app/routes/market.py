from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.market.installer import install as install_plugin
from app.market.installer import uninstall as uninstall_plugin
from app.market.registry import PluginIndexItem, RegistryIndex, fetch_registry
from app.plugins import loader


router = APIRouter(prefix="/market", tags=["market"])

AUDIT_LOG_PATH = Path(__file__).resolve().parent.parent / "market" / "audit.log"


class InstallRequest(BaseModel):
    accepted_permissions: list[str]


def _append_audit_log(plugin_id: str, version: str | None, action: str) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "id": plugin_id,
        "version": version,
        "action": action,
    }
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def _find_plugin(registry: RegistryIndex, plugin_id: str) -> PluginIndexItem:
    for item in registry.plugins:
        if item.id == plugin_id:
            return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not found")


@router.get("/registry", response_model=RegistryIndex)
async def get_registry() -> RegistryIndex:
    return await fetch_registry()


@router.post("/install/{plugin_id}")
async def install(plugin_id: str, payload: InstallRequest) -> dict[str, Any]:
    registry = await fetch_registry()
    item = _find_plugin(registry, plugin_id)

    required = set(item.permissions or [])
    accepted = set(payload.accepted_permissions or [])
    if not required.issubset(accepted):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required permissions",
        )

    result = await install_plugin(item)
    _append_audit_log(plugin_id, result.get("version"), "install")
    return {"installed": True, **result}


@router.post("/enable/{plugin_id}")
async def enable(plugin_id: str) -> dict[str, Any]:
    runtime = loader.get_runtime(plugin_id)
    if runtime is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not installed")
    loader.enable_plugin(plugin_id, {})
    _append_audit_log(plugin_id, runtime.manifest.version, "enable")
    return {"enabled": True}


@router.post("/disable/{plugin_id}")
async def disable(plugin_id: str) -> dict[str, Any]:
    runtime = loader.get_runtime(plugin_id)
    if runtime is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not installed")
    loader.disable_plugin(plugin_id, {})
    _append_audit_log(plugin_id, runtime.manifest.version, "disable")
    return {"disabled": True}


@router.post("/uninstall/{plugin_id}")
async def uninstall(plugin_id: str) -> dict[str, Any]:
    runtime = loader.get_runtime(plugin_id)
    if runtime is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not installed")
    version = runtime.manifest.version
    uninstall_plugin(plugin_id)
    _append_audit_log(plugin_id, version, "uninstall")
    return {"uninstalled": True}

