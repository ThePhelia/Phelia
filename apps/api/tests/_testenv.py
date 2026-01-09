"""Test environment bootstrap for API tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path


_DEFAULT_ENV = {
    "APP_SECRET": "test",
    "DATABASE_URL": "sqlite:///./test.db",
    "REDIS_URL": "redis://localhost:6379/0",
    "CELERY_BROKER_URL": "redis://localhost:6379/0",
    "CELERY_RESULT_BACKEND": "redis://localhost:6379/1",
    "QB_URL": "http://localhost:8080",
    "QB_USER": "test_user",
    "QB_PASS": "dummy_password",
    "ANYIO_BACKEND": "asyncio",
    "METADATA_BASE_URL": "http://metadata-proxy.test",
    "PHELIA_API_KEYS_PATH": str(Path(__file__).resolve().parent / ".test_api_keys.enc"),
}

for key, value in _DEFAULT_ENV.items():
    os.environ.setdefault(key, value)


tests_dir = Path(__file__).resolve().parent
app_dir = tests_dir.parent
sys.path.insert(0, str(app_dir))


from app.core.runtime_settings import runtime_settings  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402


__all__ = ["Base", "SessionLocal", "engine", "runtime_settings"]
