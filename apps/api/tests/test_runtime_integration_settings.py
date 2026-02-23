from app.core.runtime_integration_settings import RuntimeIntegrationSettings
from app.core.secure_store import EncryptedKeyStore, SecretsStore


def test_runtime_integrations_migrate_legacy_flat_keys(tmp_path):
    path = tmp_path / "secrets.json.enc"
    store = SecretsStore(EncryptedKeyStore(secret="test-secret", path=path))
    store.set("tmdb", "legacy-tmdb-api-key-1234")
    runtime = RuntimeIntegrationSettings(store=store)

    assert runtime.get("tmdb.api_key") == "legacy-tmdb-api-key-1234"
    section = store.load_section("integrations")
    assert section["values"]["tmdb.api_key"] == "legacy-tmdb-api-key-1234"


def test_runtime_integrations_mask_secret_values(tmp_path):
    path = tmp_path / "secrets.json.enc"
    store = SecretsStore(EncryptedKeyStore(secret="test-secret", path=path))
    runtime = RuntimeIntegrationSettings(store=store)

    runtime.set("tmdb.api_key", "1234567890abcdef")
    payload = runtime.describe(include_secrets=False)["tmdb.api_key"]

    assert payload["configured"] is True
    assert payload["value"] == "••••••••"
