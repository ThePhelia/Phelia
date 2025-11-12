#!/usr/bin/env python3
"""Build a `.phex` archive for the Jackett Integrator plugin."""

from __future__ import annotations

import argparse
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Iterable

import yaml


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def _read_manifest() -> dict:
    manifest_path = PLUGIN_ROOT / "phelia.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest at {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _copy_tree(src: Path, dest: Path) -> None:
    if not src.exists():
        return
    shutil.copytree(
        src,
        dest,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )


def _stage_files(staging: Path) -> None:
    (staging / "backend").mkdir(parents=True, exist_ok=True)
    manifest = PLUGIN_ROOT / "phelia.yaml"
    shutil.copy2(manifest, staging / "phelia.yaml")

    readme = PLUGIN_ROOT / "README.md"
    if readme.exists():
        shutil.copy2(readme, staging / "README.md")

    data_dir = PLUGIN_ROOT / "data"
    if data_dir.exists():
        _copy_tree(data_dir, staging / "data")

    compose_dir = PLUGIN_ROOT / "compose"
    if compose_dir.exists():
        _copy_tree(compose_dir, staging / "compose")

    src_dir = PLUGIN_ROOT / "src"
    backend_target = staging / "backend"
    for package in src_dir.iterdir():
        if package.name.startswith("__pycache__"):
            continue
        _copy_tree(package, backend_target / package.name)


def _iter_members(directory: Path) -> Iterable[Path]:
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            yield path


def build_archive(output: Path) -> Path:
    manifest = _read_manifest()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        staging = Path(tmpdir)
        _stage_files(staging)

        with tarfile.open(output, "w:gz") as archive:
            for member in _iter_members(staging):
                arcname = member.relative_to(staging)
                archive.add(member, arcname=str(arcname))

    return output


def main() -> int:
    manifest = _read_manifest()
    default_name = f"{manifest['id']}-{manifest['version']}.phex"
    parser = argparse.ArgumentParser(
        description="Build Jackett Integrator .phex archive"
    )
    parser.add_argument("--output", type=Path, help="Path for the generated archive")
    args = parser.parse_args()

    output = args.output or (PLUGIN_ROOT / "dist" / default_name)
    result = build_archive(output)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
