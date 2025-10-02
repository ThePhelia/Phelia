from __future__ import annotations

import hashlib
import importlib
import sys
import tarfile
import textwrap
from pathlib import Path
from uuid import uuid4

import pytest

from app.market.installer import (
    InstallerError,
    install_phex_from_file,
    install_phex_from_url,
    uninstall,
)
from app.plugins import loader


def _build_plugin_archive(
    tmp_path: Path,
    *,
    plugin_id: str | None = None,
    module_name: str | None = None,
    permissions: dict | None = None,
) -> tuple[Path, str, str]:
    plugin_id = plugin_id or f"com.phelia.tests.{uuid4().hex}"
    module_name = module_name or f"plugin_{uuid4().hex}"

    root = tmp_path / module_name
    root.mkdir()

    manifest = textwrap.dedent(
        f"""
        schema: 1
        id: {plugin_id}
        name: Test Plugin
        version: 1.0.0
        phelia:
          minVersion: "0.7.0"
          hooks:
            backend:
              entrypoint: {module_name}.main:Plugin
        """
    )
    (root / "phelia.yaml").write_text(manifest, encoding="utf-8")

    backend_dir = root / "backend" / module_name
    backend_dir.mkdir(parents=True)
    (backend_dir / "__init__.py").write_text("", encoding="utf-8")
    plugin_code = textwrap.dedent(
        """
        CALLS = []

        class Plugin:
            def on_install(self, ctx):
                CALLS.append("install")

            def on_enable(self, ctx):
                CALLS.append("enable")

            def on_disable(self, ctx):
                CALLS.append("disable")

            def on_uninstall(self, ctx):
                CALLS.append("uninstall")
        """
    )
    (backend_dir / "main.py").write_text(plugin_code, encoding="utf-8")

    if permissions:
        import yaml

        (root / "permissions.yaml").write_text(
            yaml.safe_dump(permissions), encoding="utf-8"
        )

    archive_path = tmp_path / f"{module_name}.phex"
    with tarfile.open(archive_path, "w:gz") as tar:
        for path in root.rglob("*"):
            tar.add(path, arcname=str(path.relative_to(root)))
    return archive_path, plugin_id, module_name


@pytest.fixture
def plugin_env(tmp_path: Path):
    loader.reset_state()
    plugins_dir = tmp_path / "plugins"
    loader.set_plugins_base_dir(plugins_dir)
    created_modules: list[str] = []
    yield plugins_dir, created_modules
    loader.reset_state()
    for name in created_modules:
        sys.modules.pop(name, None)


@pytest.mark.anyio
async def test_install_phex_from_file_happy_path(plugin_env: tuple[Path, list[str]], tmp_path: Path) -> None:
    _, modules = plugin_env
    archive_path, plugin_id, module_name = _build_plugin_archive(tmp_path)
    result = await install_phex_from_file(archive_path.read_bytes(), expected_sha256=None)

    assert result["status"] == "enabled"
    runtime = loader.get_runtime(plugin_id)
    assert runtime is not None
    assert runtime.enabled

    module = importlib.import_module(f"{module_name}.main")
    modules.extend([module_name, f"{module_name}.main"])
    assert module.CALLS[:2] == ["install", "enable"]


@pytest.mark.anyio
async def test_install_phex_from_url_with_expected_sha256(
    plugin_env: tuple[Path, list[str]], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, modules = plugin_env
    archive_path, plugin_id, module_name = _build_plugin_archive(tmp_path)
    archive_bytes = archive_path.read_bytes()
    expected = hashlib.sha256(archive_bytes).hexdigest()

    class DummyResponse:
        def __init__(self, content: bytes) -> None:
            self.content = content

        def raise_for_status(self) -> None:  # pragma: no cover - trivial
            return None

    async def fake_get(self, url: str, timeout: float):  # type: ignore[override]
        return DummyResponse(archive_bytes)

    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)

    result = await install_phex_from_url("https://example.com/plugin.phex", expected)
    assert result["id"] == plugin_id
    assert result["integrity_status"] in {"verified", "unsigned"}

    module = importlib.import_module(f"{module_name}.main")
    modules.extend([module_name, f"{module_name}.main"])
    assert "enable" in module.CALLS


@pytest.mark.anyio
async def test_install_failure_rolls_back_and_cleans_staging(plugin_env: tuple[Path, list[str]], tmp_path: Path) -> None:
    plugins_dir, _ = plugin_env
    bad_root = tmp_path / "bad"
    bad_root.mkdir()
    (bad_root / "phelia.yaml").write_text("schema: 2", encoding="utf-8")
    archive_path = tmp_path / "bad.phex"
    with tarfile.open(archive_path, "w:gz") as tar:
        for path in bad_root.rglob("*"):
            tar.add(path, arcname=str(path.relative_to(bad_root)))

    with pytest.raises(InstallerError):
        await install_phex_from_file(archive_path.read_bytes(), expected_sha256=None)

    staging_dir = plugins_dir / "_staging"
    if staging_dir.exists():
        assert list(staging_dir.iterdir()) == []
    assert not any(path for path in plugins_dir.iterdir() if path.name != "_staging")


@pytest.mark.anyio
async def test_enable_disable_uninstall_lifecycle_hooks(
    plugin_env: tuple[Path, list[str]], tmp_path: Path
) -> None:
    _, modules = plugin_env
    archive_path, plugin_id, module_name = _build_plugin_archive(tmp_path)
    await install_phex_from_file(archive_path.read_bytes(), expected_sha256=None)

    module = importlib.import_module(f"{module_name}.main")
    modules.extend([module_name, f"{module_name}.main"])
    assert module.CALLS == ["install", "enable"]

    loader.disable_plugin(plugin_id, {})
    assert module.CALLS[-1] == "disable"

    loader.enable_plugin(plugin_id, {})
    assert module.CALLS[-1] == "enable"

    uninstall(plugin_id)
    assert module.CALLS[-1] == "uninstall"
    assert loader.get_runtime(plugin_id) is None
    assert not loader.plugin_root_dir(plugin_id).exists()

