import httpx

from app.services.qbittorrent import health


def _response(status_code: int, body: str) -> httpx.Response:
    request = httpx.Request("POST", "http://qbittorrent:8080/api/v2/auth/login")
    return httpx.Response(status_code, text=body, request=request)


def test_qb_login_stops_retrying_on_fails_response(monkeypatch):
    calls = {"count": 0}

    def fake_post(*_args, **_kwargs):
        calls["count"] += 1
        return _response(200, "Fails.")

    monkeypatch.setenv("QBIT_PASSWORD", "wrong-pass")
    monkeypatch.setattr(health.httpx, "post", fake_post)

    result = health.qb_login_ok()

    assert result is False
    assert calls["count"] == 1

