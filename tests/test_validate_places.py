import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_FILES = [
    "andaman-and-nicobar-islands.json",
    "andhra-pradesh.json",
    "arunachal-pradesh.json",
    "assam.json",
    "bihar.json",
    "chandigarh.json",
    "chhattisgarh.json",
    "dadra-and-nagar-haveli-and-daman-and-diu.json",
    "delhi.json",
    "goa.json",
    "gujarat.json",
    "haryana.json",
    "himachal-pradesh.json",
    "jammu-and-kashmir.json",
    "jharkhand.json",
    "karnataka.json",
    "kerala.json",
    "ladakh.json",
    "lakshadweep.json",
    "madhya-pradesh.json",
    "maharashtra.json",
    "manipur.json",
    "meghalaya.json",
    "mizoram.json",
    "nagaland.json",
    "odisha.json",
    "puducherry.json",
    "punjab.json",
    "rajasthan.json",
    "sikkim.json",
    "tamil-nadu.json",
    "telangana.json",
    "tripura.json",
    "uttar-pradesh.json",
    "uttarakhand.json",
    "west-bengal.json",
]


def test_every_state_and_territory_has_places():
    data_dir = ROOT / "data" / "places"
    missing = [name for name in EXPECTED_FILES if not (data_dir / name).is_file()]
    assert not missing, missing
    total = 0
    for name in EXPECTED_FILES:
        records = json.loads((data_dir / name).read_text(encoding="utf-8"))
        assert records, name
        total += len(records)
        with_facts = sum(1 for record in records if record.get("facts"))
        assert with_facts == len(records), name
    assert total >= 40000


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
