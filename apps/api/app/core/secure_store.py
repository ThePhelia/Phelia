"""Encrypted storage for persisted API keys."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_STORE_PATH = Path("/data/secrets.json.enc")
STORE_ENV_VAR = "PHELIA_API_KEYS_PATH"
MASTER_KEY_ENV = "APP_SECRET_KEY"
MASTER_KEY_FILE_ENV = "APP_SECRET_KEY_FILE"

LEGACY_PLAINTEXT_SUFFIXES = (".json", ".api_keys.json", ".api_keys")


def _default_store_path() -> Path:
    override = os.environ.get(STORE_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return DEFAULT_STORE_PATH


def _derive_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _resolve_master_secret() -> str | None:
    secret = os.environ.get(MASTER_KEY_ENV)
    if secret:
        return secret
    secret_file = os.environ.get(MASTER_KEY_FILE_ENV)
    if secret_file:
        try:
            return Path(secret_file).read_text(encoding="utf-8").strip()
        except OSError as exc:
            logger.warning("Failed to read APP_SECRET_KEY_FILE: %s", exc)
    return settings.APP_SECRET


@dataclass(slots=True)
class EncryptedKeyStore:
    """Persist API keys encrypted with the application secret."""

    secret: str | None
    path: Path = _default_store_path()

    def _legacy_plaintext_paths(self) -> list[Path]:
        candidates: list[Path] = []
        if self.path.suffix == ".enc":
            candidates.append(self.path.with_suffix(""))
        for suffix in LEGACY_PLAINTEXT_SUFFIXES:
            candidates.append(self.path.with_suffix(suffix))
        return candidates

    def _migrate_plaintext(self) -> None:
        if self.path.exists():
            return
        for candidate in self._legacy_plaintext_paths():
            if not candidate.exists():
                continue
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                logger.warning("Failed to read legacy plaintext key store: %s", exc)
                continue
            if not isinstance(payload, dict):
                logger.warning("Legacy plaintext key store is not a dict; skipping.")
                continue
            self.save(payload)
            try:
                candidate.unlink()
            except OSError as exc:
                logger.warning("Failed to remove legacy plaintext key store: %s", exc)
            return

    def _fernet(self) -> Fernet | None:
        if not self.secret:
            return None
        return Fernet(_derive_key(self.secret))

    def load(self) -> dict[str, Any]:
        fernet = self._fernet()
        if fernet is None:
            return {}
        self._migrate_plaintext()
        if not self.path.exists():
            return {}
        try:
            payload = self.path.read_bytes()
            decrypted = fernet.decrypt(payload)
            data = json.loads(decrypted.decode("utf-8"))
        except (OSError, ValueError, InvalidToken) as exc:
            logger.warning("Failed to read encrypted API key store: %s", exc)
            return {}
        if isinstance(data, dict):
            return data
        return {}

    def save(self, data: dict[str, Any]) -> None:
        fernet = self._fernet()
        if fernet is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(data, ensure_ascii=False).encode("utf-8")
        encrypted = fernet.encrypt(serialized)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_bytes(encrypted)
        os.chmod(temp_path, 0o600)
        temp_path.replace(self.path)

    def load_section(self, section: str) -> dict[str, Any]:
        data = self.load()
        section_data = data.get(section)
        return section_data if isinstance(section_data, dict) else {}

    def save_section(self, section: str, values: dict[str, Any]) -> None:
        data = self.load()
        data[section] = values
        self.save(data)


class SecretsStore:
    """Shared secrets store with convenience helpers."""

    def __init__(self, store: EncryptedKeyStore | None = None) -> None:
        self._lock = RLock()
        self._store = store or EncryptedKeyStore(secret=_resolve_master_secret())

    def get(self, key: str) -> Any:
        with self._lock:
            return self._store.load().get(key)

    def set(self, key: str, value: Any) -> None:
        self.set_many({key: value})

    def set_many(
        self, values: dict[str, Any], allow_empty_keys: set[str] | None = None
    ) -> None:
        with self._lock:
            data = self._store.load()
            for key, value in values.items():
                if value is None or (value == "" and key not in (allow_empty_keys or set())):
                    data.pop(key, None)
                else:
                    data[key] = value
            self._store.save(data)

    def list_configured(self) -> list[str]:
        with self._lock:
            return [key for key, value in self._store.load().items() if value]

    def export_redacted(self) -> dict[str, str | None]:
        with self._lock:
            return {
                key: ("configured" if value else None)
                for key, value in self._store.load().items()
            }


def get_key_store() -> EncryptedKeyStore:
    return EncryptedKeyStore(secret=_resolve_master_secret())


def get_secrets_store() -> SecretsStore:
    return SecretsStore()


__all__ = ["EncryptedKeyStore", "SecretsStore", "get_key_store", "get_secrets_store"]
