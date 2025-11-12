"""Utilities for working with Phelia `.phex` plugin archives."""

from __future__ import annotations

import hashlib
import shutil
import tarfile
from pathlib import Path
from typing import Any, Literal, Mapping

import yaml  # type: ignore[import-untyped]
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


MAX_ARCHIVE_SIZE = 100 * 1024 * 1024  # 100 MiB safety ceiling


class PhexError(ValueError):
    """Raised when a `.phex` archive fails validation."""


def _ensure_within_directory(base: Path, target: Path) -> None:
    base_resolved = base.resolve()
    target_resolved = target.resolve()
    try:
        target_resolved.relative_to(base_resolved)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise PhexError("Archive member escapes destination directory") from exc


def safe_extract_tar_gz(archive_path: Path, dest_dir: Path) -> None:
    """Safely extract ``archive_path`` into ``dest_dir``.

    The extractor rejects entries that attempt path traversal, create links or
    FIFOs, or exceed the configured size budget. Extraction is intentionally
    strict to minimise the risk of malicious archives.
    """

    if not archive_path.exists():
        raise PhexError("Archive does not exist")

    dest_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path, "r:gz") as tar:
        members = tar.getmembers()
        total_size = 0

        for member in members:
            name = member.name
            if not name:
                raise PhexError("Archive contains entry with empty name")
            if name.startswith("/"):
                raise PhexError("Archive member uses an absolute path")
            if ".." in Path(name).parts:
                raise PhexError("Archive member attempts directory traversal")
            if member.islnk() or member.issym():
                raise PhexError("Archive contains link entries which are not allowed")
            if member.ischr() or member.isblk() or member.isfifo():
                raise PhexError("Archive contains unsupported special files")

            if member.isfile():
                total_size += max(member.size, 0)
                if total_size > MAX_ARCHIVE_SIZE:
                    raise PhexError("Archive contents exceed allowed size")

        for member in members:
            target_path = dest_dir / member.name
            target_path.parent.mkdir(parents=True, exist_ok=True)
            _ensure_within_directory(dest_dir, target_path.parent)

            if member.isdir():
                target_path.mkdir(parents=True, exist_ok=True)
                continue

            if not member.isfile():
                raise PhexError(f"Unsupported archive member type for '{member.name}'")

            extracted = tar.extractfile(member)  # type: ignore[arg-type]
            if extracted is None:
                raise PhexError(f"Unable to extract member '{member.name}'")

            with extracted as src:
                with target_path.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
            _ensure_within_directory(dest_dir, target_path)


def _require_mapping(data: Any, message: str) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise PhexError(message)
    return data


def load_phelia_manifest(staging_dir: Path) -> dict[str, Any]:
    """Load and validate ``phelia.yaml`` from ``staging_dir``."""

    manifest_path = staging_dir / "phelia.yaml"
    if not manifest_path.exists():
        raise PhexError("Missing phelia.yaml manifest")

    with manifest_path.open("r", encoding="utf-8") as fh:
        raw_data = yaml.safe_load(fh)

    manifest = _require_mapping(raw_data, "Manifest must be a mapping")

    schema = manifest.get("schema")
    if schema != 1:
        raise PhexError("Unsupported manifest schema version")

    normalized: dict[str, Any] = {"schema": 1}

    try:
        normalized["id"] = str(manifest["id"]).strip()
        normalized["name"] = str(manifest["name"]).strip()
        normalized["version"] = str(manifest["version"]).strip()
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise PhexError(f"Missing required field: {exc.args[0]}") from exc

    if not normalized["id"] or not normalized["name"] or not normalized["version"]:
        raise PhexError("Manifest fields 'id', 'name' and 'version' must be non-empty")

    description = manifest.get("description")
    if description is not None:
        normalized["description"] = str(description)

    author = manifest.get("author")
    if author is not None:
        normalized["author"] = {
            key: str(value)
            for key, value in _require_mapping(
                author, "Author must be a mapping"
            ).items()
            if value is not None
        }

    license_name = manifest.get("license")
    if license_name is not None:
        normalized["license"] = str(license_name)

    phelia_block = _require_mapping(manifest.get("phelia"), "Missing 'phelia' section")
    min_version = phelia_block.get("minVersion")
    if not isinstance(min_version, str) or not min_version.strip():
        raise PhexError("'phelia.minVersion' must be provided")
    hooks_block = _require_mapping(phelia_block.get("hooks"), "Missing 'phelia.hooks'")
    backend_block = _require_mapping(
        hooks_block.get("backend"), "Missing 'phelia.hooks.backend'"
    )
    entrypoint = backend_block.get("entrypoint")
    if not isinstance(entrypoint, str) or not entrypoint.strip():
        raise PhexError("Backend entrypoint must be specified")

    web_block = hooks_block.get("web")
    if web_block is not None:
        web_block = _require_mapping(web_block, "'phelia.hooks.web' must be a mapping")

    normalized["phelia"] = {
        "minVersion": min_version.strip(),
        "hooks": {
            "backend": {"entrypoint": entrypoint.strip()},
        },
    }
    if web_block is not None:
        normalized["phelia"]["hooks"]["web"] = {
            key: value for key, value in web_block.items() if value is not None
        }

    runtime_block = manifest.get("runtime")
    if runtime_block is not None:
        runtime_mapping = _require_mapping(runtime_block, "'runtime' must be a mapping")
        normalized["runtime"] = {}
        if "python" in runtime_mapping and runtime_mapping["python"] is not None:
            normalized["runtime"]["python"] = str(runtime_mapping["python"]).strip()
        if (
            "settingsSchema" in runtime_mapping
            and runtime_mapping["settingsSchema"] is not None
        ):
            settings_schema = runtime_mapping["settingsSchema"]
            if not isinstance(settings_schema, Mapping):
                raise PhexError("'runtime.settingsSchema' must be a mapping")
            normalized["runtime"]["settingsSchema"] = dict(settings_schema)
    else:
        normalized["runtime"] = {}

    integrity_block = manifest.get("integrity")
    if integrity_block is not None:
        integrity_mapping = _require_mapping(
            integrity_block, "'integrity' must be a mapping"
        )
        normalized["integrity"] = {
            key: str(value)
            for key, value in integrity_mapping.items()
            if isinstance(value, str)
        }

    normalized["entrypoint"] = entrypoint.strip()

    return normalized


def verify_integrity(
    archive_path: Path,
    manifest: Mapping[str, Any],
    sig_path: Path | None,
    pubkey_path: Path | None,
) -> Literal["verified", "unsigned", "invalid"]:
    """Validate archive integrity using the manifest and optional signature."""

    digest = hashlib.sha256()
    with archive_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    hexdigest = digest.hexdigest()

    integrity_info = manifest.get("integrity")
    manifest_sha = None
    if isinstance(integrity_info, Mapping):
        manifest_sha = integrity_info.get("sha256")

    if isinstance(manifest_sha, str):
        if hexdigest.lower() != manifest_sha.lower():
            return "invalid"
        sha_matches = True
    else:
        sha_matches = False

    if sig_path and pubkey_path and sig_path.exists() and pubkey_path.exists():
        signature = sig_path.read_bytes()
        public_key_bytes = pubkey_path.read_bytes()
        try:
            verify_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            verify_key.verify(signature, bytes.fromhex(hexdigest))
            return "verified"
        except (InvalidSignature, ValueError):
            return "invalid"

    if sha_matches:
        return "verified"

    return "unsigned"
