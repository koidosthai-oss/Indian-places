import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_validate_places_exits_zero():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_places.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "Validated" in result.stdout
