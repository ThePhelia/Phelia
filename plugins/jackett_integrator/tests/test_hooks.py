from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from jackett_integrator import hooks


def test_find_plugin_root_detects_manifest() -> None:
    root = hooks.find_plugin_root()
    assert (root / "phelia.yaml").exists()


def test_wait_for_api_key_reads_server_config(tmp_path: Path) -> None:
    jackett_dir = tmp_path / "Jackett"
    jackett_dir.mkdir(parents=True)
    (jackett_dir / "ServerConfig.json").write_text('{"APIKey": "abc123"}', encoding="utf-8")

    api_key = hooks.wait_for_api_key(tmp_path, timeout=0.1, interval=0.01)

    assert api_key == "abc123"


def test_compose_up_builds_expected_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PHELIA_PLUGIN_SKIP_DOCKER", "0")

    plugin_root = tmp_path / "plugin"
    (plugin_root / "compose").mkdir(parents=True)
    (plugin_root / "compose" / "docker-compose.override.yml").write_text("version: '3.9'\n", encoding="utf-8")
    (plugin_root / "phelia.yaml").write_text("schema: 1\nid: test\nname: test\nversion: 0.0.1\nphelia:\n  minVersion: '0.7.0'\n  hooks:\n    backend:\n      entrypoint: dummy\n", encoding="utf-8")

    base_compose = tmp_path / "base-compose.yml"
    base_compose.write_text("version: '3.9'\nservices: {}\n", encoding="utf-8")
    monkeypatch.setenv("PHELIA_COMPOSE_FILE", str(base_compose))

    captured = {}

    def fake_run(cmd, capture_output, text):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("jackett_integrator.hooks.subprocess.run", fake_run)

    hooks.compose_up(plugin_root)

    assert captured["cmd"][:4] == ["docker", "compose", "-f", str(base_compose)]
    assert "jackett" in captured["cmd"]
