import pytest

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
