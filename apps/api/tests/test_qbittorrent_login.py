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
    def __init__(self, response: httpx.Response | list[httpx.Response]):
        self.responses = response if isinstance(response, list) else [response]
        self.cookies = self.responses[0].cookies

    async def post(self, *_args, **_kwargs):
        response = self.responses.pop(0)
        self.cookies = response.cookies
        return response


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
async def test_login_maps_403_to_auth_failed():
    response = _response(403, "Forbidden")
    qb = QbClient("http://qb", "user", "pass")
    dummy = DummyAsyncClient(response)
    qb._client = dummy
    qb._c = lambda: dummy

    with pytest.raises(QbittorrentLoginError) as excinfo:
        await qb.login()

    assert excinfo.value.code == "AUTH_FAILED"


@pytest.mark.anyio
async def test_login_uses_temporary_password_from_logs(monkeypatch):
    first = _response(200, "Fails.")
    second = _response(200, "Ok.", {"set-cookie": "SID=from-temp"})
    qb = QbClient("http://qb", "admin", "configured-pass")
    dummy = DummyAsyncClient([first, second])
    qb._client = dummy
    qb._c = lambda: dummy

    saved = {}

    def _update_qbittorrent(*, password=None, **_kwargs):
        saved["password"] = password

    monkeypatch.setattr(
        "app.services.bt.qbittorrent._read_temporary_password",
        lambda: "temp-pass",
    )
    monkeypatch.setattr(
        "app.services.bt.qbittorrent.runtime_service_settings.update_qbittorrent",
        _update_qbittorrent,
    )

    await qb.login()

    assert qb.password == "temp-pass"
    assert saved["password"] == "temp-pass"


def test_read_temporary_password_prefers_file_logs(monkeypatch):
    monkeypatch.setattr(
        "app.services.bt.qbittorrent._read_temporary_password_from_logs",
        lambda: "from-files",
    )
    monkeypatch.setattr(
        "app.services.bt.qbittorrent._read_temporary_password_from_container_logs",
        lambda: "from-container",
    )

    from app.services.bt.qbittorrent import _read_temporary_password

    assert _read_temporary_password() == "from-files"


def test_read_temporary_password_falls_back_to_container_logs(monkeypatch):
    monkeypatch.setattr(
        "app.services.bt.qbittorrent._read_temporary_password_from_logs",
        lambda: None,
    )
    monkeypatch.setattr(
        "app.services.bt.qbittorrent._read_temporary_password_from_container_logs",
        lambda: "from-container",
    )

    from app.services.bt.qbittorrent import _read_temporary_password

    assert _read_temporary_password() == "from-container"
