from app.core.runtime_service_settings import RuntimeServiceSettings
from app.core.secure_store import EncryptedKeyStore, SecretsStore


def _store(tmp_path):
    path = tmp_path / "secrets.json.enc"
    return SecretsStore(EncryptedKeyStore(secret="secret", path=path))


def test_qbittorrent_update_preserves_other_keys(tmp_path):
    store = _store(tmp_path)
    store.set_many({"jackett_api_key": "jackett", "extra_key": "keep"})
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
