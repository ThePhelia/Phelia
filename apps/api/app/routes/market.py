from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status, Form
from pydantic import BaseModel, ConfigDict, Field

from app.market.installer import (
    InstallerError,
    install_phex_from_file,
    install_phex_from_url,
    uninstall as uninstall_plugin,
)
from app.market.registry import (
    RegistryIndex,
    RegistryUnavailableError,
    fetch_registry,
)
from app.plugins import loader


router = APIRouter(prefix="/market", tags=["market"])

AUDIT_LOG_PATH = Path(__file__).resolve().parent.parent / "market" / "audit.log"


class UrlInstallRequest(BaseModel):
    url: str
    expected_sha256: str | None = Field(default=None, alias="expectedSha256")

    model_config = ConfigDict(populate_by_name=True)


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


def _runtime_summary(runtime: loader.PluginRuntime) -> dict[str, Any]:
    return {
        "id": runtime.manifest.id,
        "name": runtime.manifest.name,
        "version": runtime.manifest.version,
        "status": runtime.status,
        "integrity_status": runtime.integrity_status,
        "sha256": runtime.sha256,
        "permissions": runtime.permissions,
        "source": runtime.source,
        "last_error": runtime.last_error,
    }


@router.get("/registry", response_model=RegistryIndex)
async def get_registry() -> RegistryIndex:
    try:
        return await fetch_registry()
    except RegistryUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=error.detail,
        ) from error


@router.get("/plugins")
def list_plugins() -> list[dict[str, Any]]:
    runtimes = loader.list_plugins()
    return [_runtime_summary(runtime) for runtime in runtimes]


@router.post("/plugins/install/upload")
async def install_plugin_from_upload(
    file: UploadFile = File(...),
    expected_sha256: str | None = Form(default=None, alias="expectedSha256"),
) -> dict[str, Any]:
    data = await file.read()
    try:
        result = await install_phex_from_file(data, expected_sha256)
    except InstallerError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exc.code, "message": str(exc)},
        )
    _append_audit_log(result["id"], result.get("version"), "install_upload")
    return result


@router.post("/plugins/install/url")
async def install_plugin_from_url(payload: UrlInstallRequest) -> dict[str, Any]:
    try:
        result = await install_phex_from_url(payload.url, payload.expected_sha256)
    except InstallerError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exc.code, "message": str(exc)},
        )
    _append_audit_log(result["id"], result.get("version"), "install_url")
    return result


@router.post("/plugins/enable/{plugin_id}")
async def enable(plugin_id: str) -> dict[str, Any]:
    runtime = loader.get_runtime(plugin_id)
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not installed"
        )
    loader.enable_plugin(plugin_id, {})
    _append_audit_log(plugin_id, runtime.manifest.version, "enable")
    return _runtime_summary(loader.get_runtime(plugin_id) or runtime)


@router.post("/plugins/disable/{plugin_id}")
async def disable(plugin_id: str) -> dict[str, Any]:
    runtime = loader.get_runtime(plugin_id)
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not installed"
        )
    loader.disable_plugin(plugin_id, {})
    _append_audit_log(plugin_id, runtime.manifest.version, "disable")
    updated = loader.get_runtime(plugin_id) or runtime
    return _runtime_summary(updated)


@router.post("/plugins/uninstall/{plugin_id}")
async def uninstall(plugin_id: str) -> dict[str, Any]:
    runtime = loader.get_runtime(plugin_id)
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not installed"
        )
    uninstall_plugin(plugin_id)
    _append_audit_log(plugin_id, runtime.manifest.version, "uninstall")
    return {"id": plugin_id, "uninstalled": True}
