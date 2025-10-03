import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.market import registry as registry_module


@pytest.mark.anyio
async def test_market_registry_handles_registry_unavailable(monkeypatch):
    class FailingAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, *args, **kwargs):
            request = httpx.Request("GET", url)
            response = httpx.Response(503, request=request)
            raise httpx.HTTPStatusError(
                "Service unavailable",
                request=request,
                response=response,
            )

    monkeypatch.setattr(
        registry_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: FailingAsyncClient(),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/market/registry")

    assert response.status_code == 502
    assert response.json() == {"detail": "Registry request failed with status 503"}
