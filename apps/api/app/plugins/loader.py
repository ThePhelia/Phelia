from __future__ import annotations

import importlib
import inspect
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping
from typing import Any

from .manifest import PluginManifest
from app.db.session import session_scope
from app.services import plugin_settings as plugin_settings_service


PLUGINS_DIR = Path(os.getenv("PLUGINS_DIR", "/app/plugins"))
PLUGINS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PluginRuntime:
    manifest: PluginManifest
    instance: Any
    enabled: bool = False


_RUNTIMES: dict[str, PluginRuntime] = {}


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


def _manifest_path(plugin_dir: Path) -> Path:
    return plugin_dir / "manifest.json"


def _site_packages_dir(plugin_dir: Path) -> Path:
    return plugin_dir / "site"


def import_entry(site_dir: Path, entry_point: str) -> Any:
    if site_dir.exists():
        site_str = str(site_dir)
        if site_str not in sys.path:
            sys.path.append(site_str)
    module_name, _, attr = entry_point.partition(":")
    if not module_name or not attr:
        raise ValueError(f"Invalid entry point '{entry_point}'")
    module = importlib.import_module(module_name)
    target = getattr(module, attr)
    if inspect.isclass(target):
        return target()
    if callable(target):
        return target()
    return target


def discover_installed() -> list[PluginManifest]:
    manifests: list[PluginManifest] = []
    if not PLUGINS_DIR.exists():
        return manifests
    for child in PLUGINS_DIR.iterdir():
        if not child.is_dir():
            continue
        manifest_file = _manifest_path(child)
        if not manifest_file.exists():
            continue
        with manifest_file.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        manifest = PluginManifest.model_validate(data)
        previous = _RUNTIMES.get(manifest.id)
        if previous is not None:
            if manifest.settings_schema is None and previous.manifest.settings_schema is not None:
                manifest.settings_schema = previous.manifest.settings_schema
            if (
                manifest.contributes_settings is None
                and previous.manifest.contributes_settings is not None
            ):
                manifest.contributes_settings = previous.manifest.contributes_settings
        if manifest.contributes_settings is None and manifest.settings_schema is not None:
            manifest.contributes_settings = True
        manifests.append(manifest)
        site_dir = _site_packages_dir(child)
        instance = import_entry(site_dir, manifest.entry_point)
        _RUNTIMES[manifest.id] = PluginRuntime(
            manifest=manifest,
            instance=instance,
            enabled=previous.enabled if previous else False,
        )
    return manifests


def _get_runtime(plugin_id: str) -> PluginRuntime:
    runtime = _RUNTIMES.get(plugin_id)
    if runtime is None:
        discover_installed()
        runtime = _RUNTIMES.get(plugin_id)
    if runtime is None:
        raise KeyError(f"Plugin '{plugin_id}' not installed")
    return runtime


def list_plugins() -> list[PluginRuntime]:
    """Return the runtime metadata for all discovered plugins."""

    discover_installed()
    return list(_RUNTIMES.values())


def register_plugin(manifest: PluginManifest, instance: Any) -> None:
    _RUNTIMES[manifest.id] = PluginRuntime(manifest=manifest, instance=instance)


def register_settings_panel(plugin_id: str, schema: dict[str, Any]) -> None:
    runtime = _get_runtime(plugin_id)
    runtime.manifest.settings_schema = schema
    runtime.manifest.contributes_settings = True


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

    return prepared


def enable_plugin(plugin_id: str, ctx: dict[str, Any] | None = None) -> None:
    runtime = _get_runtime(plugin_id)
    if runtime.enabled:
        return
    prepared_ctx = _prepare_context(plugin_id, ctx)
    hook = getattr(runtime.instance, "on_enable", None)
    if callable(hook):
        hook(prepared_ctx)
    runtime.enabled = True


def disable_plugin(plugin_id: str, ctx: dict[str, Any] | None = None) -> None:
    runtime = _get_runtime(plugin_id)
    if not runtime.enabled:
        return
    prepared_ctx = _prepare_context(plugin_id, ctx)
    hook = getattr(runtime.instance, "on_disable", None)
    if callable(hook):
        hook(prepared_ctx)
    runtime.enabled = False


def remove_plugin(plugin_id: str) -> None:
    _RUNTIMES.pop(plugin_id, None)


def get_runtime(plugin_id: str) -> PluginRuntime | None:
    runtime = _RUNTIMES.get(plugin_id)
    if runtime is not None:
        return runtime
    try:
        return _get_runtime(plugin_id)
    except KeyError:
        return None


def plugin_site_dir(plugin_id: str) -> Path:
    return _site_packages_dir(PLUGINS_DIR / plugin_id)


def plugin_root_dir(plugin_id: str) -> Path:
    return PLUGINS_DIR / plugin_id

