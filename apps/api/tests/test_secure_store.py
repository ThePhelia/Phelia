from app.core.runtime_settings import RuntimeProviderSettings
from app.core.secure_store import EncryptedKeyStore, SecretsStore


def test_secrets_store_persists_encrypted(tmp_path):
    path = tmp_path / "secrets.json.enc"
    store = SecretsStore(EncryptedKeyStore(secret="test-secret", path=path))
    store.set("lastfm", "abc123")
    store.set("listenbrainz", "token456")

    payload = path.read_bytes()
    assert b"abc123" not in payload
    assert b"token456" not in payload

    reloaded = SecretsStore(EncryptedKeyStore(secret="test-secret", path=path))
    assert reloaded.get("lastfm") == "abc123"
    assert reloaded.get("listenbrainz") == "token456"


def test_runtime_settings_update_does_not_erase_other_keys(tmp_path):
    path = tmp_path / "secrets.json.enc"
    store = SecretsStore(EncryptedKeyStore(secret="test-secret", path=path))
    settings = RuntimeProviderSettings(store=store)

    settings.update_many({"lastfm": "alpha", "listenbrainz": "beta"})
    settings.set("lastfm", "gamma")

    assert settings.get("lastfm") == "gamma"
    assert settings.get("listenbrainz") == "beta"

    reloaded = RuntimeProviderSettings(store=SecretsStore(EncryptedKeyStore(secret="test-secret", path=path)))
    assert reloaded.get("lastfm") == "gamma"
    assert reloaded.get("listenbrainz") == "beta"
