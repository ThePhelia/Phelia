"""Runtime loader for Phelia plugins backed by `.phex` archives."""

from __future__ import annotations

import importlib
import inspect
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

from app.db.session import session_scope
from app.market.phex import load_phelia_manifest
from app.plugins.manifest import PluginManifest
from app.services import plugin_settings as plugin_settings_service


DEFAULT_PLUGINS_DIR = Path(os.getenv("PLUGINS_DIR", "/app/plugins"))
STATE_FILENAME = "state.json"
CURRENT_VERSION_FILENAME = "current"
VERSIONS_DIRNAME = "versions"
LOG_DIRNAME = "logs"
LOG_FILENAME = "plugin.log"
MAX_LOG_BYTES = 512 * 1024
LOG_BACKUP_COUNT = 3


PLUGINS_DIR = DEFAULT_PLUGINS_DIR
PLUGINS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PluginRuntime:
    """In-memory representation of a loaded plugin."""

    manifest: PluginManifest
    path: Path
    site_dir: Path
    status: str = "installed"
    instance: Any | None = None
    integrity_status: str = "unsigned"
    sha256: str | None = None
    source: str | None = None
    permissions: list[str] = field(default_factory=list)
    last_error: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    logger: logging.Logger | None = None

    @property
    def enabled(self) -> bool:
        return self.status == "enabled"


_RUNTIMES: dict[str, PluginRuntime] = {}


def set_plugins_base_dir(path: Path) -> None:
    """Override the plugins directory (used primarily for testing)."""

    global PLUGINS_DIR
    PLUGINS_DIR = path
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)


def reset_state() -> None:
    """Reset runtime caches (used in tests)."""

    _RUNTIMES.clear()


def get_plugins_base_dir() -> Path:
    return PLUGINS_DIR


def plugin_root_dir(plugin_id: str) -> Path:
    return PLUGINS_DIR / plugin_id


def _versions_dir(plugin_id: str) -> Path:
    return plugin_root_dir(plugin_id) / VERSIONS_DIRNAME


def plugin_version_dir(plugin_id: str, version: str) -> Path:
    return _versions_dir(plugin_id) / version


def plugin_site_dir(plugin_id: str, version: str | None = None) -> Path:
    version_name = version or _read_current_version(plugin_id)
    if not version_name:
        raise KeyError(f"Plugin '{plugin_id}' is not installed")
    return plugin_version_dir(plugin_id, version_name) / "site"


def _state_path(plugin_id: str) -> Path:
    return plugin_root_dir(plugin_id) / STATE_FILENAME


def _current_version_path(plugin_id: str) -> Path:
    return plugin_root_dir(plugin_id) / CURRENT_VERSION_FILENAME


def _logs_dir(plugin_id: str) -> Path:
    return plugin_root_dir(plugin_id) / LOG_DIRNAME


def _read_current_version(plugin_id: str) -> str | None:
    path = _current_version_path(plugin_id)
    if not path.exists():
        return None
    value = path.read_text(encoding="utf-8").strip()
    return value or None


def _write_current_version(plugin_id: str, version: str) -> None:
    path = _current_version_path(plugin_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(version, encoding="utf-8")


def _available_versions(plugin_id: str) -> list[str]:
    versions_dir = _versions_dir(plugin_id)
    if not versions_dir.exists():
        return []
    return sorted(entry.name for entry in versions_dir.iterdir() if entry.is_dir())


def _read_state(plugin_id: str) -> dict[str, Any]:
    path = _state_path(plugin_id)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


def _write_state(plugin_id: str, state: Mapping[str, Any]) -> None:
    path = _state_path(plugin_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)


def _parse_permissions(raw: Any, prefix: str = "") -> list[str]:
    permissions: list[str] = []
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            key_str = str(key)
            next_prefix = f"{prefix}:{key_str}" if prefix else key_str
            permissions.extend(_parse_permissions(value, next_prefix))
    elif isinstance(raw, list):
        for value in raw:
            permissions.extend(_parse_permissions(value, prefix))
    elif raw is None:
        if prefix:
            permissions.append(prefix)
    else:
        value_str = str(raw)
        permissions.append(f"{prefix}:{value_str}" if prefix else value_str)
    return permissions


def _load_permissions(plugin_dir: Path) -> list[str]:
    permissions_path = plugin_dir / "permissions.yaml"
    if not permissions_path.exists():
        return []
    with permissions_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return _parse_permissions(data) if data is not None else []


def _configure_logger(plugin_id: str) -> logging.Logger:
    logger_name = f"phelia.plugin.{plugin_id}"
    logger = logging.getLogger(logger_name)
    if not logger.handlers:
        logs_dir = _logs_dir(plugin_id)
        logs_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            logs_dir / LOG_FILENAME,
            maxBytes=MAX_LOG_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


class PluginSettingsStore:
    """Convenience wrapper for plugin settings CRUD operations."""

    def __init__(self, plugin_id: str) -> None:
        self._plugin_id = plugin_id

    def get(self, key: str, default: Any | None = None) -> Any:
        with session_scope() as db:
            value = plugin_settings_service.get_setting(db, self._plugin_id, key)
        return default if value is None else value

    def all(self) -> dict[str, Any]:
        with session_scope() as db:
            return plugin_settings_service.get_settings(db, self._plugin_id)

    def set(self, key: str, value: Any) -> None:
        with session_scope() as db:
            plugin_settings_service.set_value(db, self._plugin_id, key, value)

    def set_many(self, values: Mapping[str, Any]) -> None:
        for key, value in values.items():
            self.set(key, value)

    def clear(self) -> None:
        with session_scope() as db:
            plugin_settings_service.delete_settings(db, self._plugin_id)


def _prepare_context(plugin_id: str, ctx: dict[str, Any] | None) -> dict[str, Any]:
    prepared: dict[str, Any] = {}
    if ctx:
        prepared.update(ctx)

    store = prepared.get("settings_store")
    if not isinstance(store, PluginSettingsStore):
        store = PluginSettingsStore(plugin_id)
        prepared["settings_store"] = store

    if "settings_get" not in prepared:
        prepared["settings_get"] = store.get
    if "settings_set" not in prepared:
        prepared["settings_set"] = store.set_many

    def _register(target_plugin_id: str, schema: dict[str, Any]) -> None:
        if target_plugin_id != plugin_id:
            raise ValueError("Plugin ID mismatch when registering settings panel")
        register_settings_panel(target_plugin_id, schema)

    if "register_settings_panel" not in prepared:
        prepared["register_settings_panel"] = _register

    logger = _configure_logger(plugin_id)
    prepared.setdefault("logger", logger)

    return prepared


def _ensure_instance(runtime: PluginRuntime) -> Any:
    if runtime.instance is not None:
        return runtime.instance

    plugin_dir = runtime.path
    site_dir = runtime.site_dir
    backend_dir = plugin_dir / "backend"

    for candidate in (site_dir, backend_dir, plugin_dir):
        if candidate.exists():
            candidate_str = str(candidate)
            if candidate_str not in sys.path:
                sys.path.append(candidate_str)

    module_name, _, attr = runtime.manifest.entry_point.partition(":")
    if not module_name or not attr:
        raise ValueError(f"Invalid entry point '{runtime.manifest.entry_point}'")

    module = importlib.import_module(module_name)
    target = getattr(module, attr)
    if inspect.isclass(target):
        runtime.instance = target()
    elif callable(target):
        runtime.instance = target()
    else:
        runtime.instance = target
    return runtime.instance


def _load_manifest_from_path(plugin_dir: Path) -> Mapping[str, Any]:
    return load_phelia_manifest(plugin_dir)


def _build_runtime(plugin_id: str, version: str, state: Mapping[str, Any]) -> PluginRuntime:
    install_dir = plugin_version_dir(plugin_id, version)
    manifest_data = _load_manifest_from_path(install_dir)
    hooks = manifest_data.get("phelia", {}).get("hooks", {}) if isinstance(manifest_data, Mapping) else {}
    web_assets = None
    if isinstance(hooks, Mapping):
        web_block = hooks.get("web")
        if isinstance(web_block, Mapping):
            assets_path = web_block.get("assetsPath")
            if isinstance(assets_path, str):
                web_assets = assets_path

    permissions = _load_permissions(install_dir)
    manifest = PluginManifest.from_yaml_mapping(manifest_data, permissions, web_assets)

    runtime = PluginRuntime(
        manifest=manifest,
        path=install_dir,
        site_dir=install_dir / "site",
        status=str(state.get("status", "installed")),
        integrity_status=str(state.get("integrity", "unsigned")),
        sha256=state.get("sha256"),
        source=state.get("source"),
        permissions=permissions,
        last_error=state.get("last_error"),
    )

    updated_at = state.get("updated_at")
    if isinstance(updated_at, str):
        try:
            runtime.updated_at = datetime.fromisoformat(updated_at)
        except ValueError:
            runtime.updated_at = datetime.now(timezone.utc)

    runtime.logger = _configure_logger(plugin_id)

    return runtime


def _refresh_runtime(plugin_id: str) -> PluginRuntime | None:
    state = _read_state(plugin_id)
    version = _read_current_version(plugin_id)
    if not version:
        available = _available_versions(plugin_id)
        if not available:
            return None
        version = available[-1]
        _write_current_version(plugin_id, version)

    runtime = _build_runtime(plugin_id, version, state)
    _RUNTIMES[runtime.manifest.id] = runtime
    return runtime


def discover_installed() -> list[PluginRuntime]:
    runtimes: list[PluginRuntime] = []
    if not PLUGINS_DIR.exists():
        return runtimes

    for entry in PLUGINS_DIR.iterdir():
        if not entry.is_dir():
            continue
        runtime = _refresh_runtime(entry.name)
        if runtime is None:
            continue
        runtimes.append(runtime)
    return runtimes


def _get_runtime(plugin_id: str) -> PluginRuntime:
    runtime = _RUNTIMES.get(plugin_id)
    if runtime is None:
        discover_installed()
        runtime = _RUNTIMES.get(plugin_id)
    if runtime is None:
        raise KeyError(f"Plugin '{plugin_id}' not installed")
    return runtime


def list_plugins() -> list[PluginRuntime]:
    discover_installed()
    return list(_RUNTIMES.values())


def register_settings_panel(plugin_id: str, schema: dict[str, Any]) -> None:
    runtime = _get_runtime(plugin_id)
    runtime.manifest.settings_schema = schema


def update_runtime_state(plugin_id: str, **changes: Any) -> None:
    state = _read_state(plugin_id)
    state.update(changes)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_state(plugin_id, state)


def register_runtime(runtime: PluginRuntime) -> None:
    _RUNTIMES[runtime.manifest.id] = runtime
    _write_current_version(runtime.manifest.id, runtime.manifest.version)
    update_runtime_state(
        runtime.manifest.id,
        status=runtime.status,
        integrity=runtime.integrity_status,
        sha256=runtime.sha256,
        source=runtime.source,
        permissions=runtime.permissions,
        last_error=runtime.last_error,
        current_version=runtime.manifest.version,
    )


def read_permissions(directory: Path) -> list[str]:
    """Public helper for reading permissions from a plugin directory."""

    return _load_permissions(directory)


def enable_plugin(plugin_id: str, ctx: dict[str, Any] | None = None) -> None:
    runtime = _get_runtime(plugin_id)
    if runtime.enabled:
        return

    prepared_ctx = _prepare_context(plugin_id, ctx)
    instance = _ensure_instance(runtime)

    hook = getattr(instance, "on_enable", None)
    if callable(hook):
        hook(prepared_ctx)

    register_routes = getattr(instance, "register_routes", None)
    if callable(register_routes) and "app" in prepared_ctx:
        register_routes(prepared_ctx["app"])

    register_tasks = getattr(instance, "register_tasks", None)
    if callable(register_tasks) and "celery" in prepared_ctx:
        register_tasks(prepared_ctx["celery"])

    runtime.status = "enabled"
    runtime.last_error = None
    runtime.updated_at = datetime.now(timezone.utc)
    update_runtime_state(
        plugin_id,
        status="enabled",
        last_error=None,
        permissions=runtime.permissions,
    )


def disable_plugin(plugin_id: str, ctx: dict[str, Any] | None = None) -> None:
    runtime = _get_runtime(plugin_id)
    if not runtime.enabled:
        return

    prepared_ctx = _prepare_context(plugin_id, ctx)
    instance = _ensure_instance(runtime)

    hook = getattr(instance, "on_disable", None)
    if callable(hook):
        hook(prepared_ctx)

    runtime.status = "disabled"
    runtime.updated_at = datetime.now(timezone.utc)
    update_runtime_state(plugin_id, status="disabled")


def run_install_hook(plugin_id: str, ctx: dict[str, Any] | None = None) -> None:
    runtime = _get_runtime(plugin_id)
    instance = _ensure_instance(runtime)
    hook = getattr(instance, "on_install", None)
    if callable(hook):
        prepared_ctx = _prepare_context(plugin_id, ctx)
        hook(prepared_ctx)


def run_uninstall_hook(plugin_id: str, ctx: dict[str, Any] | None = None) -> None:
    runtime = _get_runtime(plugin_id)
    instance = _ensure_instance(runtime)
    hook = getattr(instance, "on_uninstall", None)
    if callable(hook):
        prepared_ctx = _prepare_context(plugin_id, ctx)
        hook(prepared_ctx)


def remove_plugin(plugin_id: str) -> None:
    _RUNTIMES.pop(plugin_id, None)
    update_runtime_state(plugin_id, status="uninstalled")


def get_runtime(plugin_id: str) -> PluginRuntime | None:
    runtime = _RUNTIMES.get(plugin_id)
    if runtime is not None:
        return runtime
    try:
        return _get_runtime(plugin_id)
    except KeyError:
        return None

