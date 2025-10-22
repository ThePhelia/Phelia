"""Lifecycle helpers for the Jackett Integrator plugin."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Sequence


LOGGER = logging.getLogger(__name__)


def _docker_disabled() -> bool:
    return os.getenv("PHELIA_PLUGIN_SKIP_DOCKER") == "1"


def find_plugin_root(start: Path | None = None) -> Path:
    """Return the plugin root directory containing ``phelia.yaml``."""

    path = start or Path(__file__).resolve()
    for candidate in [path, *path.parents]:
        manifest = candidate / "phelia.yaml"
        if manifest.exists():
            return candidate
    raise RuntimeError("Unable to locate plugin root")


def _detect_base_compose(root: Path) -> Path:
    env_path = os.getenv("PHELIA_COMPOSE_FILE")
    if env_path:
        candidate = Path(env_path)
        if candidate.exists():
            return candidate
    for candidate in root.parents:
        compose_path = candidate / "deploy" / "docker-compose.yml"
        if compose_path.exists():
            return compose_path
    # Fallback to default container path used by bundled images.
    return Path("/app/deploy/docker-compose.yml")


def compose_files(root: Path) -> tuple[Path, Path]:
    base = _detect_base_compose(root)
    override = root / "compose" / "docker-compose.override.yml"
    if not override.exists():
        raise FileNotFoundError(f"Missing compose override at {override}")
    return base, override


def ensure_config_dir(root: Path) -> Path:
    config_dir = root / "data" / "jackett_config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def run_compose(root: Path, args: Sequence[str]) -> None:
    if _docker_disabled():
        LOGGER.info("Skipping docker compose %s because docker integration is disabled", args)
        return
    base, override = compose_files(root)
    command = ["docker", "compose", "-f", str(base), "-f", str(override), *args]
    LOGGER.info("Executing %s", " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        LOGGER.error("docker compose failed: %s", result.stderr.strip())
        raise RuntimeError(f"docker compose command failed: {' '.join(command)}")


def compose_up(root: Path) -> None:
    run_compose(root, ["up", "-d", "jackett"])


def compose_stop(root: Path) -> None:
    run_compose(root, ["stop", "jackett"])


def compose_remove(root: Path) -> None:
    run_compose(root, ["rm", "-sf", "jackett"])


def _server_config_path(config_dir: Path) -> Path:
    return config_dir / "Jackett" / "ServerConfig.json"


def wait_for_api_key(config_dir: Path, timeout: float = 120.0, interval: float = 2.0) -> str | None:
    """Poll Jackett's ServerConfig until the API key becomes available."""

    deadline = time.time() + timeout
    target = _server_config_path(config_dir)
    while time.time() < deadline:
        if not target.exists():
            time.sleep(interval)
            continue
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            LOGGER.debug("ServerConfig.json not yet ready, retrying...")
            time.sleep(interval)
            continue
        api_key = data.get("APIKey")
        if isinstance(api_key, str) and api_key.strip():
            return api_key.strip()
        time.sleep(interval)
    return None


__all__ = [
    "compose_files",
    "compose_remove",
    "compose_stop",
    "compose_up",
    "ensure_config_dir",
    "find_plugin_root",
    "wait_for_api_key",
    "run_compose",
]
