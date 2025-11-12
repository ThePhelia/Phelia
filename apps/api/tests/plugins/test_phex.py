from __future__ import annotations

import hashlib
import io
import tarfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.market.phex import (
    PhexError,
    load_phelia_manifest,
    safe_extract_tar_gz,
    verify_integrity,
)
from app.plugins.manifest import PluginManifest


def _create_tar_with_member(
    path: Path, member: tarfile.TarInfo, data: bytes | None = None
) -> None:
    with tarfile.open(path, "w:gz") as tar:
        if data is None:
            tar.addfile(member)
        else:
            tar.addfile(member, io.BytesIO(data))


def test_phex_safe_extract_blocks_symlinks_and_traversal(tmp_path: Path) -> None:
    symlink_tar = tmp_path / "symlink.tar.gz"
    sym_info = tarfile.TarInfo("malicious")
    sym_info.type = tarfile.SYMTYPE
    sym_info.linkname = "/etc/passwd"
    _create_tar_with_member(symlink_tar, sym_info)

    with pytest.raises(PhexError):
        safe_extract_tar_gz(symlink_tar, tmp_path / "dest1")

    traversal_tar = tmp_path / "traversal.tar.gz"
    trav_info = tarfile.TarInfo("../escape.txt")
    payload = b"escape"
    trav_info.size = len(payload)
    _create_tar_with_member(traversal_tar, trav_info, payload)

    with pytest.raises(PhexError):
        safe_extract_tar_gz(traversal_tar, tmp_path / "dest2")


def test_phex_manifest_yaml_parsed_to_model(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    manifest_text = """
    schema: 1
    id: com.phelia.plugins.example
    name: Example Plugin
    version: 1.0.0
    description: Adds feature X.
    author:
      name: ACME Dev
      email: dev@example.com
    license: MIT
    phelia:
      minVersion: "0.7.0"
      hooks:
        backend:
          entrypoint: example_plugin.main:Plugin
        web:
          assetsPath: web/dist
    runtime:
      python: ">=3.12"
      settingsSchema:
        properties:
          apiKey:
            type: string
    integrity:
      sha256: deadbeef
    """
    (staging / "phelia.yaml").write_text(manifest_text, encoding="utf-8")
    permissions_file = """
    network:
      outbound:
        - https://example.com
    """
    (staging / "permissions.yaml").write_text(permissions_file, encoding="utf-8")

    manifest_data = load_phelia_manifest(staging)
    permissions = ["network:outbound:https://example.com"]
    manifest = PluginManifest.from_yaml_mapping(
        manifest_data, permissions=permissions, web_assets_path="web/dist"
    )

    assert manifest.id == "com.phelia.plugins.example"
    assert manifest.entry_point == "example_plugin.main:Plugin"
    assert manifest.permissions == permissions
    assert manifest.web_assets_path == "web/dist"
    assert manifest.integrity_sha256 == "deadbeef"


def test_phex_integrity_sha256_match_and_mismatch(tmp_path: Path) -> None:
    archive = tmp_path / "archive.tar.gz"
    archive.write_bytes(b"sample")
    digest = hashlib.sha256(b"sample").hexdigest()
    manifest = {"integrity": {"sha256": digest}}

    assert verify_integrity(archive, manifest, None, None) == "verified"

    manifest_bad = {"integrity": {"sha256": "0000"}}
    assert verify_integrity(archive, manifest_bad, None, None) == "invalid"


def test_phex_signature_valid_and_invalid(tmp_path: Path) -> None:
    archive = tmp_path / "archive.tar.gz"
    data = b"signature-test"
    archive.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    signature = private_key.sign(bytes.fromhex(digest))
    (tmp_path / "signature.sig").write_bytes(signature)
    (tmp_path / "public.pem").write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )

    manifest = {}
    assert (
        verify_integrity(
            archive,
            manifest,
            tmp_path / "signature.sig",
            tmp_path / "public.pem",
        )
        == "verified"
    )

    bad_signature = signature[:-1] + b"0"
    (tmp_path / "signature.sig").write_bytes(bad_signature)
    assert (
        verify_integrity(
            archive,
            manifest,
            tmp_path / "signature.sig",
            tmp_path / "public.pem",
        )
        == "invalid"
    )
