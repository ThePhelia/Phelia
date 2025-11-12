"""Smoke tests for the FastAPI application wiring."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import fastapi

ROOT = Path(__file__).resolve().parents[2]
API_SRC = ROOT / "apps" / "api"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))


def test_api_app_exposes_fastapi_instance() -> None:
    try:
        module = import_module("app.main")
        assert isinstance(module.app, fastapi.FastAPI)
    except ImportError as e:
        # If import fails, try to provide more context
        import os
        print(f"Import failed: {e}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Python path: {sys.path[:5]}")
        print(f"API_SRC exists: {API_SRC.exists()}")
        print(f"API_SRC contents: {list(API_SRC.iterdir()) if API_SRC.exists() else 'N/A'}")
        raise


def test_health_router_registered() -> None:
    module = import_module("app.main")
    routes = {route.path for route in module.app.routes}
    assert "/api/v1/healthz" in routes
