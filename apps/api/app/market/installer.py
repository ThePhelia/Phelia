"""Installer utilities for `.phex` plugins."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Any

import httpx
from packaging.version import InvalidVersion, Version

from app.core.version import get_version as get_phelia_version
from app.market.phex import (
    PhexError,
    load_phelia_manifest,
    safe_extract_tar_gz,
    verify_integrity,
)
from app.plugins.loader import (
    PluginRuntime,
    disable_plugin,
    enable_plugin,
    get_plugins_base_dir,
    get_runtime,
    plugin_root_dir,
    plugin_version_dir,
    read_permissions,
    register_runtime,
    remove_plugin,
    run_install_hook,
    run_uninstall_hook,
)
from app.plugins.manifest import PluginManifest
from app.db.session import session_scope
from app.services import plugin_settings as plugin_settings_service


MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
DOWNLOAD_TIMEOUT = 60.0


def _normalize_expected_digest(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


class InstallerError(RuntimeError):
    """Raised when installing a plugin fails."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _ensure_size_limit(size: int) -> None:
    if size > MAX_ARCHIVE_BYTES:
        raise InstallerError("archive_too_large", "Archive exceeds the maximum allowed size")


def _staging_dir() -> Path:
    path = get_plugins_base_dir() / "_staging"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _create_temp_archive(data: bytes) -> Path:
    _ensure_size_limit(len(data))
    with tempfile.NamedTemporaryFile(dir=_staging_dir(), delete=False) as tmp:
        tmp.write(data)
        return Path(tmp.name)


def _compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _remove_metadata_entries(path: Path) -> None:
    """Drop packaging artefacts that should not affect installation."""

    macos_dir = path / "__MACOSX"
    if macos_dir.exists():
        shutil.rmtree(macos_dir, ignore_errors=True)

    for ds_store in path.glob(".DS_Store"):
        ds_store.unlink(missing_ok=True)


def _determine_plugin_root(staging_dir: Path) -> Path:
    """Return the directory that contains the plugin manifest."""

    _remove_metadata_entries(staging_dir)

    manifest_path = staging_dir / "phelia.yaml"
    if manifest_path.exists():
        return staging_dir

    candidate_dirs = [
        entry
        for entry in staging_dir.iterdir()
        if entry.is_dir() and (entry / "phelia.yaml").exists()
    ]

    if len(candidate_dirs) == 1:
        return candidate_dirs[0]

    raise PhexError("Missing phelia.yaml manifest")


def _prepare_site_directory(plugin_root: Path) -> Path:
    site_dir = plugin_root / "site"
    if site_dir.exists():
        shutil.rmtree(site_dir)
    site_dir.mkdir(parents=True, exist_ok=True)

    backend_dir = plugin_root / "backend"
    if backend_dir.exists():
        for entry in backend_dir.iterdir():
            if entry.name in {"pyproject.toml", "requirements.txt"}:
                continue
            destination = site_dir / entry.name
            if entry.is_dir():
                shutil.copytree(entry, destination)
            else:
                shutil.copy2(entry, destination)

    return site_dir


def _select_web_assets(manifest_data: dict[str, Any]) -> str | None:
    hooks = manifest_data.get("phelia", {}).get("hooks", {})
    if isinstance(hooks, dict):
        web_block = hooks.get("web")
        if isinstance(web_block, dict):
            assets_path = web_block.get("assetsPath")
            if isinstance(assets_path, str):
                return assets_path
    return None


def _parse_manifest(plugin_root: Path) -> tuple[dict[str, Any], PluginManifest, list[str]]:
    manifest_data = load_phelia_manifest(plugin_root)
    permissions = read_permissions(plugin_root)
    web_assets = _select_web_assets(manifest_data)
    manifest_model = PluginManifest.from_yaml_mapping(
        manifest_data,
        permissions=permissions,
        web_assets_path=web_assets,
    )
    return manifest_data, manifest_model, permissions


def _validate_version_compatibility(manifest: PluginManifest) -> None:
    current_version = get_phelia_version()
    try:
        current = Version(current_version)
        minimum = Version(manifest.min_phelia)
    except InvalidVersion as exc:  # pragma: no cover - defensive guard
        raise InstallerError("invalid_version", "Invalid semantic version encountered") from exc

    if current < minimum:
        raise InstallerError(
            "incompatible_version",
            f"Plugin requires Phelia >= {manifest.min_phelia}",
        )


def _enforce_permissions_gate(existing: PluginRuntime | None, permissions: list[str]) -> None:
    if existing is None:
        return
    old = set(existing.permissions or [])
    new = set(permissions)
    missing = new - old
    if missing:
        raise InstallerError(
            "permissions_changed",
            "Plugin requests additional permissions: " + ", ".join(sorted(missing)),
        )


async def install_phex_from_file(
    file_bytes: bytes,
    expected_sha256: str | None,
) -> dict[str, Any]:
    normalized_expected = _normalize_expected_digest(expected_sha256)
    archive_path = _create_temp_archive(file_bytes)
    try:
        digest = _compute_sha256(archive_path)
        digest_lower = digest.lower()
        if normalized_expected and digest_lower != normalized_expected:
            raise InstallerError("sha256_mismatch", "Uploaded archive SHA-256 does not match")
        return await _install_from_archive(archive_path, digest, source="upload")
    finally:
        if archive_path.exists():
            archive_path.unlink()


async def install_phex_from_url(
    url: str,
    expected_sha256: str | None,
) -> dict[str, Any]:
    normalized_expected = _normalize_expected_digest(expected_sha256)
    async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT) as client:
        response = await client.get(url, timeout=DOWNLOAD_TIMEOUT)
        response.raise_for_status()
        data = response.content

    archive_path = _create_temp_archive(data)
    try:
        digest = _compute_sha256(archive_path)
        digest_lower = digest.lower()
        if normalized_expected and digest_lower != normalized_expected:
            raise InstallerError("sha256_mismatch", "Downloaded archive SHA-256 does not match")
        return await _install_from_archive(archive_path, digest, source="url")
    finally:
        if archive_path.exists():
            archive_path.unlink()


async def _install_from_archive(archive_path: Path, digest: str, source: str) -> dict[str, Any]:
    staging_root = _staging_dir()
    staging_path = Path(tempfile.mkdtemp(dir=staging_root))
    cleanup_candidate = staging_path
    existing_runtime: PluginRuntime | None = None
    was_enabled = False
    target_dir: Path | None = None

    try:
        safe_extract_tar_gz(archive_path, staging_path)
        extracted_root = _determine_plugin_root(staging_path)
        manifest_data, manifest_model, permissions = _parse_manifest(extracted_root)

        _validate_version_compatibility(manifest_model)

        sig_path = extracted_root / "signature.sig"
        pubkey_path = extracted_root / "public.pem"
        integrity_status = verify_integrity(
            archive_path,
            manifest_data,
            sig_path if sig_path.exists() else None,
            pubkey_path if pubkey_path.exists() else None,
        )
        if integrity_status == "invalid":
            raise InstallerError("invalid_integrity", "Archive integrity verification failed")

        existing_runtime = get_runtime(manifest_model.id)
        if existing_runtime:
            was_enabled = existing_runtime.enabled
            _enforce_permissions_gate(existing_runtime, permissions)
            if was_enabled:
                disable_plugin(manifest_model.id, {})

        _prepare_site_directory(extracted_root)

        plugin_root = plugin_root_dir(manifest_model.id)
        versions_dir = plugin_root / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)
        target_dir = plugin_version_dir(manifest_model.id, manifest_model.version)
        if target_dir.exists():
            shutil.rmtree(target_dir)

        shutil.move(str(extracted_root), str(target_dir))
        if extracted_root != staging_path:
            shutil.rmtree(staging_path, ignore_errors=True)
        staging_path = target_dir  # Avoid cleanup deleting the moved directory
        cleanup_candidate = staging_path

        runtime = PluginRuntime(
            manifest=manifest_model,
            path=target_dir,
            site_dir=target_dir / "site",
            status="installed",
            integrity_status=integrity_status,
            sha256=digest,
            source=source,
            permissions=permissions,
        )

        register_runtime(runtime)

        if existing_runtime is None:
            run_install_hook(manifest_model.id, {})

        enable_plugin(manifest_model.id, {})

        result = {
            "id": manifest_model.id,
            "name": manifest_model.name,
            "version": manifest_model.version,
            "sha256": digest,
            "integrity": integrity_status,
            "integrity_status": integrity_status,
            "status": get_runtime(manifest_model.id).status,
            "permissions": permissions,
            "source": source,
        }
        return result
    except PhexError as exc:
        raise InstallerError("invalid_archive", str(exc)) from exc
    except InstallerError:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        if target_dir and target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        if existing_runtime is not None:
            register_runtime(existing_runtime)
            if was_enabled:
                enable_plugin(existing_runtime.manifest.id, {})
        raise InstallerError("internal_error", str(exc)) from exc
    finally:
        if (
            cleanup_candidate.exists()
            and cleanup_candidate.is_dir()
            and cleanup_candidate.parent == staging_root
        ):
            shutil.rmtree(cleanup_candidate, ignore_errors=True)


def uninstall(plugin_id: str) -> None:
    runtime = get_runtime(plugin_id)
    if runtime is None:
        return

    if runtime.enabled:
        disable_plugin(plugin_id, {})

    run_uninstall_hook(plugin_id, {})

    with session_scope() as db:
        plugin_settings_service.delete_settings(db, plugin_id)

    remove_plugin(plugin_id)

    plugin_dir = plugin_root_dir(plugin_id)
    if plugin_dir.exists():
        shutil.rmtree(plugin_dir)

