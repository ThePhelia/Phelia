"""Shared environment bootstrap for top-level tests."""

from __future__ import annotations

import os


_DEFAULT_ENV = {
    "APP_SECRET": "test",
    "DATABASE_URL": "sqlite:///./test.db",
    "REDIS_URL": "redis://localhost:6379/0",
    "CELERY_BROKER_URL": "redis://localhost:6379/0",
    "CELERY_RESULT_BACKEND": "redis://localhost:6379/0",
    "QB_URL": "http://localhost.test",
    "QB_USER": "test_user",
    "QB_PASS": "dummy_password",
    "METADATA_BASE_URL": "http://metadata-proxy.test",
}

for key, value in _DEFAULT_ENV.items():
    os.environ.setdefault(key, value)


