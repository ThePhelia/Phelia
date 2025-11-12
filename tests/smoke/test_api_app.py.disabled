"""Smoke tests for the FastAPI application wiring."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add the API source to Python path
ROOT = Path(__file__).resolve().parents[2]
API_SRC = ROOT / "apps" / "api"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

# Set required environment variables for the test
os.environ.setdefault("APP_SECRET", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("METADATA_BASE_URL", "http://metadata-proxy.test")


def test_api_app_can_be_imported() -> None:
    """Test that the API app module can be imported successfully."""
    try:
        # Import FastAPI first to ensure it's available
        import fastapi
        
        # Try to import the main module
        from app import main
        
        # Check that the app is a FastAPI instance
        assert hasattr(main, 'app'), "main module should have an 'app' attribute"
        assert isinstance(main.app, fastapi.FastAPI), "app should be a FastAPI instance"
        
    except ImportError as e:
        # If import fails, provide debugging information
        print(f"Import failed: {e}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Python path: {sys.path[:5]}")
        print(f"API_SRC: {API_SRC}")
        print(f"API_SRC exists: {API_SRC.exists()}")
        if API_SRC.exists():
            print(f"API_SRC contents: {list(API_SRC.iterdir())}")
            app_dir = API_SRC / "app"
            if app_dir.exists():
                print(f"app directory contents: {list(app_dir.iterdir())}")
        raise
