import asyncio
import logging
from contextlib import contextmanager

from app import main


def _stub_session_scope():
    @contextmanager
    def _cm():
        yield None

    return _cm


def test_init_db_exception_logged(monkeypatch, caplog):
    def bad_init():
        raise RuntimeError("init failure")

    monkeypatch.setattr(main, "init_db", bad_init)
    monkeypatch.setattr(main, "session_scope", _stub_session_scope())
    monkeypatch.setattr(main, "load_provider_credentials", lambda db: None)

    async def noop_qb_health_check():
        return None

    monkeypatch.setattr(main, "qb_health_check", noop_qb_health_check)

    with caplog.at_level(logging.ERROR, logger=main.logger.name):
        asyncio.run(main.startup_event())

    assert any("Error initializing database" in record.message for record in caplog.records)


def test_provider_credential_exception_logged(monkeypatch, caplog):
    monkeypatch.setattr(main, "init_db", lambda: None)

    def bad_loader(_db):
        raise RuntimeError("load failure")

    monkeypatch.setattr(main, "session_scope", _stub_session_scope())
    monkeypatch.setattr(main, "load_provider_credentials", bad_loader)

    async def noop_qb_health_check():
        return None

    monkeypatch.setattr(main, "qb_health_check", noop_qb_health_check)

    with caplog.at_level(logging.ERROR, logger=main.logger.name):
        asyncio.run(main.startup_event())

    assert any("Error loading provider credentials" in record.message for record in caplog.records)


def test_qb_health_check_exception_logged(monkeypatch, caplog):
    monkeypatch.setattr(main, "init_db", lambda: None)
    monkeypatch.setattr(main, "session_scope", _stub_session_scope())
    monkeypatch.setattr(main, "load_provider_credentials", lambda db: None)

    async def bad_qb_health_check():
        raise RuntimeError("qb failure")

    monkeypatch.setattr(main, "qb_health_check", bad_qb_health_check)

    with caplog.at_level(logging.ERROR, logger=main.logger.name):
        asyncio.run(main.startup_event())

    assert any("Error checking qBittorrent connectivity" in record.message for record in caplog.records)
