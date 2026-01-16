import httpx
import pytest

from app.services.bt.qbittorrent import QbClient, QbittorrentLoginError


def _response(status_code: int, body: str, headers: dict | None = None) -> httpx.Response:
    request = httpx.Request("POST", "http://qb/api/v2/auth/login")
    return httpx.Response(
        status_code,
        content=body.encode("utf-8"),
        headers=headers or {},
        request=request,
    )


class DummyAsyncClient:
    def __init__(self, response: httpx.Response):
        self.response = response
        self.cookies = response.cookies

    async def post(self, *_args, **_kwargs):
        return self.response


@pytest.mark.anyio
async def test_login_success_sets_cookie():
    response = _response(200, "Ok.", {"set-cookie": "SID=abc"})
    qb = QbClient("http://qb", "user", "pass")
    dummy = DummyAsyncClient(response)
    qb._client = dummy
    qb._c = lambda: dummy

    await qb.login()


@pytest.mark.anyio
async def test_login_fails_on_auth_failure():
    response = _response(200, "Fails.")
    qb = QbClient("http://qb", "user", "pass")
    dummy = DummyAsyncClient(response)
    qb._client = dummy
    qb._c = lambda: dummy

    with pytest.raises(QbittorrentLoginError) as excinfo:
        await qb.login()

    assert excinfo.value.code == "AUTH_FAILED"


@pytest.mark.anyio
async def test_login_fails_without_cookie():
    response = _response(200, "Ok.")
    qb = QbClient("http://qb", "user", "pass")
    dummy = DummyAsyncClient(response)
    qb._client = dummy
    qb._c = lambda: dummy

    with pytest.raises(QbittorrentLoginError) as excinfo:
        await qb.login()

    assert excinfo.value.code == "NO_SID_COOKIE"


@pytest.mark.anyio
async def test_login_fails_on_non_200():
    response = _response(403, "Forbidden")
    qb = QbClient("http://qb", "user", "pass")
    dummy = DummyAsyncClient(response)
    qb._client = dummy
    qb._c = lambda: dummy

    with pytest.raises(QbittorrentLoginError) as excinfo:
        await qb.login()

    assert excinfo.value.code == "HTTP_STATUS"
