from __future__ import annotations

import importlib
import inspect
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .manifest import PluginManifest


PLUGINS_DIR = Path(os.getenv("PLUGINS_DIR", "/app/plugins"))
PLUGINS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PluginRuntime:
    manifest: PluginManifest
    instance: Any
    enabled: bool = False


_RUNTIMES: dict[str, PluginRuntime] = {}


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
        manifests.append(manifest)
        site_dir = _site_packages_dir(child)
        instance = import_entry(site_dir, manifest.entry_point)
        previous = _RUNTIMES.get(manifest.id)
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


def register_plugin(manifest: PluginManifest, instance: Any) -> None:
    _RUNTIMES[manifest.id] = PluginRuntime(manifest=manifest, instance=instance)


def enable_plugin(plugin_id: str, ctx: dict[str, Any]) -> None:
    runtime = _get_runtime(plugin_id)
    if runtime.enabled:
        return
    hook = getattr(runtime.instance, "on_enable", None)
    if callable(hook):
        hook(ctx)
    runtime.enabled = True


def disable_plugin(plugin_id: str, ctx: dict[str, Any]) -> None:
    runtime = _get_runtime(plugin_id)
    if not runtime.enabled:
        return
    hook = getattr(runtime.instance, "on_disable", None)
    if callable(hook):
        hook(ctx)
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

