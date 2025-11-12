import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.routers.auth import router as auth_router


@pytest.mark.anyio
async def test_register_returns_token_and_checks_unique():
    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/auth/register", json={"email": "a@b.com", "password": "pw"}
        )
    assert resp.status_code == 201
    body = resp.json()
    assert "accessToken" in body

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_dup = await ac.post(
            "/api/v1/auth/register", json={"email": "a@b.com", "password": "pw"}
        )
    assert resp_dup.status_code == 400
