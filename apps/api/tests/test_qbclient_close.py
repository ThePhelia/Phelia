import os, sys
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

from app.services.bt.qbittorrent import QbClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_close_method_closes_underlying_client():
    qb = QbClient("http://test", "u", "p")
    client = qb._c()
    assert not client.is_closed
    await qb.close()
    assert client.is_closed


@pytest.mark.anyio
async def test_context_manager_closes_client():
    qb = QbClient("http://test", "u", "p")
    async with qb as q:
        client = q._c()
        assert not client.is_closed
    # after context exit, the client should be closed
    assert client.is_closed
