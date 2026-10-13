import json
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "data" / "schema.json"


def test_validate_empty_master_list():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_places.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "Validated 0 place(s)" in result.stdout


def test_schema_accepts_sample_record():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    record = {
        "name": "Chitkul",
        "local_name": None,
        "type": "hidden_gem",
        "state": "Himachal Pradesh",
        "district": "Kinnaur",
        "subdistrict_tehsil": None,
        "latitude": 31.3504,
        "longitude": 78.4812,
        "sources": ["manual-sample"],
        "notes": "Sample record for schema smoke test.",
        "collected_date": "2026-10-13",
        "verified": False,
    }
    validator.validate(record)
