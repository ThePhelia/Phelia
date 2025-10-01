import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.anyio
async def test_removed_jackett_route_returns_410():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/jackett/_removed")

    assert response.status_code == 410
    assert response.json() == {"detail": "Jackett integration was removed from core."}
