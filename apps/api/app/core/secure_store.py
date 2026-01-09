"""Encrypted storage for persisted API keys."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_STORE_DIR = ".phelia"
DEFAULT_STORE_FILENAME = ".api_keys.enc"
STORE_ENV_VAR = "PHELIA_API_KEYS_PATH"


def _default_store_path() -> Path:
    override = os.environ.get(STORE_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path.home() / DEFAULT_STORE_DIR / DEFAULT_STORE_FILENAME


def _derive_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@dataclass(slots=True)
class EncryptedKeyStore:
    """Persist API keys encrypted with the application secret."""

    secret: str | None
    path: Path = _default_store_path()

    def _fernet(self) -> Fernet | None:
        if not self.secret:
            return None
        return Fernet(_derive_key(self.secret))

    def load(self) -> dict[str, Any]:
        fernet = self._fernet()
        if fernet is None:
            return {}
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


def get_key_store() -> EncryptedKeyStore:
    return EncryptedKeyStore(secret=settings.APP_SECRET)


__all__ = ["EncryptedKeyStore", "get_key_store"]
