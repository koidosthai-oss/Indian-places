import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import harvest_pictures as hp

PLACES = ROOT / "data" / "places"
PICTURES = ROOT / "data" / "picture-overlay"


def test_picture_references_match_catalog_places():
    files = [path for path in PICTURES.glob("*.json") if path.name != "searched-ids.json"]
    assert files
    for path in files:
        places = {record["id"]: record for record in json.loads((PLACES / path.name).read_text(encoding="utf-8"))}
        rows = json.loads(path.read_text(encoding="utf-8"))
        assert rows
        for item in rows:
            source = places[item["id"]]
            assert item["name"] == source["name"]
            assert item["state"] == source["state"]
            assert 1 <= len(item["images"]) <= 5
            for image in item["images"]:
                assert image["image_url"].startswith("https://upload.wikimedia.org/")
                assert image["source_url"].startswith("https://commons.wikimedia.org/wiki/File:")
                assert image["license_note"]
                assert hp.file_is_local(item["name"], item["state"], image["title"])
