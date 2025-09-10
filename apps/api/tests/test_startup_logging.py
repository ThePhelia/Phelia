import os
import sys
import logging
import asyncio
import pytest

# Ensure environment variables for Settings before importing the app
os.environ.setdefault("APP_SECRET", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("QB_URL", "http://localhost:8080")
os.environ.setdefault("QB_USER", "admin")
os.environ.setdefault("QB_PASS", "adminadmin")
os.environ.setdefault("ANYIO_BACKEND", "asyncio")

# Add apps/api to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import main


def test_init_db_exception_logged(monkeypatch, caplog):
    def bad_init():
        raise RuntimeError("init failure")

    monkeypatch.setattr(main, "init_db", bad_init)
    monkeypatch.setattr(main, "ensure_jackett_tracker", lambda: None)

    async def noop_qb_health_check():
        return None

    monkeypatch.setattr(main, "qb_health_check", noop_qb_health_check)

    with caplog.at_level(logging.ERROR, logger=main.logger.name):
        asyncio.run(main.startup_event())

    assert any("Error initializing database" in record.message for record in caplog.records)


def test_ensure_jackett_tracker_exception_logged(monkeypatch, caplog):
    monkeypatch.setattr(main, "init_db", lambda: None)

    def bad_jackett():
        raise RuntimeError("jackett failure")

    monkeypatch.setattr(main, "ensure_jackett_tracker", bad_jackett)

    async def noop_qb_health_check():
        return None

    monkeypatch.setattr(main, "qb_health_check", noop_qb_health_check)

    with caplog.at_level(logging.ERROR, logger=main.logger.name):
        asyncio.run(main.startup_event())

    assert any("Error ensuring Jackett tracker" in record.message for record in caplog.records)
