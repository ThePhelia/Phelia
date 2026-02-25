from pathlib import Path

from app.core.runtime_service_settings import RuntimeServiceSettings
from app.core.secure_store import EncryptedKeyStore, SecretsStore


def _store(tmp_path):
    path = tmp_path / "secrets.json.enc"
    return SecretsStore(EncryptedKeyStore(secret="secret", path=path))


def _write_qb_config(path: Path, *, username: str, password_pbkdf2: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "[Preferences]",
                f"WebUI\\Username={username}",
                f"WebUI\\Password_PBKDF2={password_pbkdf2}",
            ]
        ),
        encoding="utf-8",
    )


def test_qbittorrent_update_preserves_other_keys(tmp_path):
    store = _store(tmp_path)
    store.set_many({"prowlarr_api_key": "prowlarr", "extra_key": "keep"})
    runtime = RuntimeServiceSettings(store=store)

    runtime.update_qbittorrent(
        url="http://qb.example",
        username="alice",
        password="s3cret",
    )

    assert store.get("extra_key") == "keep"


def test_qbittorrent_snapshot_refreshes_from_store(tmp_path):
    store = _store(tmp_path)
    store.set_many(
        {
            "qbittorrent_url": "http://qb.initial",
            "qbittorrent_username": "first",
            "qbittorrent_password": "firstpass",
        },
        allow_empty_keys={"qbittorrent_password"},
    )
    runtime = RuntimeServiceSettings(store=store)

    store.set_many(
        {
            "qbittorrent_url": "http://qb.updated",
            "qbittorrent_username": "second",
            "qbittorrent_password": "secondpass",
        },
        allow_empty_keys={"qbittorrent_password"},
    )

    snapshot = runtime.qbittorrent_snapshot()

    assert snapshot.url == "http://qb.updated"
    assert snapshot.username == "second"
    assert snapshot.password == "secondpass"


def test_reset_to_env_prefers_store_url_and_qb_volume_username(monkeypatch, tmp_path):
    qbit_conf = tmp_path / "qBittorrent" / "qBittorrent.conf"
    _write_qb_config(qbit_conf, username="qb-volume-user", password_pbkdf2="@Variant(\\0\\0)")

    monkeypatch.setattr(
        "app.core.runtime_service_settings._QBITTORRENT_CONFIG_PATHS",
        (qbit_conf,),
    )

    store = _store(tmp_path)
    store.set_many(
        {
            "qbittorrent_url": "http://persisted-qb:8080/",
            "qbittorrent_username": "stale-store-user",
            "qbittorrent_password": "persisted-password",
        },
        allow_empty_keys={"qbittorrent_password"},
    )

    runtime = RuntimeServiceSettings(store=store)
    snapshot = runtime.qbittorrent_snapshot()

    assert snapshot.url == "http://persisted-qb:8080"
    assert snapshot.username == "qb-volume-user"
    assert snapshot.password == "persisted-password"


def test_reset_to_env_detects_external_qb_password_change(monkeypatch, tmp_path, caplog):
    qbit_conf = tmp_path / "qBittorrent" / "qBittorrent.conf"
    _write_qb_config(qbit_conf, username="qb-user", password_pbkdf2="hash-from-volume-v2")

    monkeypatch.setattr(
        "app.core.runtime_service_settings._QBITTORRENT_CONFIG_PATHS",
        (qbit_conf,),
    )
    monkeypatch.setattr("app.core.runtime_service_settings.settings.QB_PASS", "env-pass")

    store = _store(tmp_path)
    store.set_many(
        {
            "qbittorrent_username": "qb-user",
            "qbittorrent_password": "old-store-password",
            "qbittorrent_password_fingerprint": "stale-fingerprint",
        },
        allow_empty_keys={"qbittorrent_password"},
    )

    caplog.set_level("WARNING")
    runtime = RuntimeServiceSettings(store=store)
    snapshot = runtime.qbittorrent_snapshot()

    assert snapshot.password == "env-pass"
    assert store.get("qbittorrent_password") == "env-pass"
    assert store.get("qbittorrent_password_fingerprint") != "stale-fingerprint"
    assert "changed externally" in caplog.text


def test_reset_to_env_keeps_password_unconfigured_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("app.core.runtime_service_settings.settings.QB_PASS", "")

    store = _store(tmp_path)
    runtime = RuntimeServiceSettings(store=store)
    snapshot = runtime.qbittorrent_snapshot()

    assert snapshot.password == ""
    assert store.get("qbittorrent_password") == ""


def test_snapshot_for_api_reports_qbittorrent_password_unconfigured(monkeypatch, tmp_path):
    monkeypatch.setattr("app.core.runtime_service_settings.settings.QB_PASS", "")

    store = _store(tmp_path)
    runtime = RuntimeServiceSettings(store=store)

    snapshot = runtime.snapshot_for_api()

    assert snapshot["qbittorrent_password_configured"] is False
