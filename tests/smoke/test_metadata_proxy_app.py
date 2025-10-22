"""Metadata proxy smoke coverage."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import fastapi

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = ROOT / "services" / "metadata-proxy" / "app"
MAIN_PATH = PACKAGE_DIR / "main.py"
PACKAGE_NAME = "metadata_proxy_app"


def _load_metadata_module():
    package = sys.modules.get(PACKAGE_NAME)
    if package is None:
        package = types.ModuleType(PACKAGE_NAME)
        package.__path__ = [str(PACKAGE_DIR)]
        sys.modules[PACKAGE_NAME] = package
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE_NAME}.main",
        MAIN_PATH,
        submodule_search_locations=[str(PACKAGE_DIR)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load metadata proxy main module")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = PACKAGE_NAME
    sys.modules[f"{PACKAGE_NAME}.main"] = module
    spec.loader.exec_module(module)
    return module


def test_metadata_proxy_factory_returns_fastapi_app() -> None:
    module = _load_metadata_module()
    app = module.create_app()
    assert isinstance(app, fastapi.FastAPI)


def test_metadata_proxy_health_route_present() -> None:
    module = _load_metadata_module()
    app = module.create_app()
    routes = {route.path for route in app.routes}
    assert "/health" in routes
