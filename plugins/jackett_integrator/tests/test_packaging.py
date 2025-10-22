from __future__ import annotations

import tarfile
from pathlib import Path
import subprocess
import sys


PLUGIN_DIR = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN_DIR / "scripts" / "build_phex.py"


def test_build_script_produces_archive(tmp_path: Path) -> None:
    output = tmp_path / "jackett.phex"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert output.exists()

    with tarfile.open(output, "r:gz") as archive:
        members = {member.name for member in archive.getmembers()}
    assert "phelia.yaml" in members
    assert "backend/jackett_integrator/plugin.py" in members
    assert "backend/jackett_integrator/provider.py" in members
