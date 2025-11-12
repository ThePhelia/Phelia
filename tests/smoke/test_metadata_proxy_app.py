"""Metadata proxy smoke coverage."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add the metadata-proxy source to Python path
ROOT = Path(__file__).resolve().parents[2]
METADATA_SRC = ROOT / "services" / "metadata-proxy"
if str(METADATA_SRC) not in sys.path:
    sys.path.insert(0, str(METADATA_SRC))

# Set required environment variables for the test
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


def test_metadata_proxy_can_be_imported() -> None:
    """Test that the metadata proxy app can be imported successfully."""
    try:
        # Import FastAPI first to ensure it's available
        import fastapi
        
        # Try to import the main module
        from app import main
        
        # Check that create_app function exists and returns a FastAPI instance
        assert hasattr(main, 'create_app'), "main module should have a 'create_app' function"
        app = main.create_app()
        assert isinstance(app, fastapi.FastAPI), "create_app should return a FastAPI instance"
        
    except ImportError as e:
        # If import fails, provide debugging information
        print(f"Import failed: {e}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Python path: {sys.path[:5]}")
        print(f"METADATA_SRC: {METADATA_SRC}")
        print(f"METADATA_SRC exists: {METADATA_SRC.exists()}")
        if METADATA_SRC.exists():
            print(f"METADATA_SRC contents: {list(METADATA_SRC.iterdir())}")
            app_dir = METADATA_SRC / "app"
            if app_dir.exists():
                print(f"app directory contents: {list(app_dir.iterdir())}")
        raise


def test_metadata_proxy_health_route_present() -> None:
    """Test that the metadata proxy has a health route."""
    try:
        from app import main
        app = main.create_app()
        routes = {route.path for route in app.routes}
        assert "/health" in routes, f"Health route not found. Available routes: {routes}"
        
    except ImportError as e:
        print(f"Import failed: {e}")
        raise
