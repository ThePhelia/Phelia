from concurrent.futures import ThreadPoolExecutor

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


def test_concurrent_saves_do_not_raise_when_writing_same_file(tmp_path):
    path = tmp_path / "secrets.json.enc"

    def write_value(index: int):
        store = EncryptedKeyStore(secret="test-secret", path=path)
        store.save({"value": index})

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(write_value, i) for i in range(40)]
        for future in futures:
            future.result()

    loaded = EncryptedKeyStore(secret="test-secret", path=path).load()
    assert "value" in loaded


def test_store_path_env_fallback(monkeypatch, tmp_path):
    from app.core import secure_store

    path = tmp_path / "shared.enc"
    monkeypatch.setenv("SECRETS_STORE_PATH", str(path))
    monkeypatch.delenv("PHELIA_API_KEYS_PATH", raising=False)

    store = secure_store.SecretsStore(secure_store.EncryptedKeyStore(secret="test-secret", path=secure_store._default_store_path()))
    store.set("tmdb.api_key", "abc1234567890123")

    reloaded = secure_store.SecretsStore(secure_store.EncryptedKeyStore(secret="test-secret", path=secure_store._default_store_path()))
    assert reloaded.get("tmdb.api_key") == "abc1234567890123"
