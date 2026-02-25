import httpx
import pytest

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


@pytest.mark.parametrize(
    ("status_code", "body"),
    [
        (401, "Unauthorized"),
        (401, "FAILS DUE TO BAD CREDENTIALS"),
        (401, "Invalid username or password"),
        (403, "Forbidden"),
        (403, "BAD CREDENTIALS"),
        (403, "Wrong Username or Password"),
    ],
)
def test_qb_login_fails_fast_on_deterministic_auth_errors(monkeypatch, status_code, body):
    calls = {"count": 0}

    def fake_post(*_args, **_kwargs):
        calls["count"] += 1
        return _response(status_code, body)

    monkeypatch.setenv("QBIT_PASSWORD", "wrong-pass")
    monkeypatch.setenv("QBIT_HEALTH_TRIES", "5")
    monkeypatch.setattr(health.httpx, "post", fake_post)

    result = health.qb_login_ok()

    assert result is False
    assert calls["count"] == 1


@pytest.mark.parametrize(
    "body",
    [
        "temporarily unavailable",
        "SERVICE UNAVAILABLE",
        "Try Again",
    ],
)
def test_qb_login_retries_on_transient_401_403(monkeypatch, body):
    calls = {"count": 0}

    def fake_post(*_args, **_kwargs):
        calls["count"] += 1
        return _response(401 if calls["count"] % 2 else 403, body)

    monkeypatch.setenv("QBIT_PASSWORD", "wrong-pass")
    monkeypatch.setenv("QBIT_HEALTH_TRIES", "3")
    monkeypatch.setattr(health.httpx, "post", fake_post)
    monkeypatch.setattr(health.time, "sleep", lambda *_args, **_kwargs: None)

    result = health.qb_login_ok()

    assert result is False
    assert calls["count"] == 3
