import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACES = ROOT / "data" / "places"
OVERLAY = ROOT / "data" / "enrichment-overlay"
ALLOWED_BASES = {
    "catalog-record",
    "regional-climate",
    "category-planning",
    "catalog-coordinates",
    "catalog-tags",
    "cited-source",
}


def test_overlay_matches_every_place_without_moving_state():
    coverage = json.loads((ROOT / "data" / "coverage-summary.json").read_text(encoding="utf-8"))
    seen = 0
    for path in sorted(PLACES.glob("*.json")):
        places = json.loads(path.read_text(encoding="utf-8"))
        overlay = json.loads((OVERLAY / path.name).read_text(encoding="utf-8"))
        assert [item["id"] for item in overlay] == sorted(record["id"] for record in places)
        by_id = {record["id"]: record for record in places}
        assert len(by_id) == len(places)
        for item in overlay:
            source = by_id[item["id"]]
            assert item["name"] == source["name"]
            assert item["state"] == source["state"]
            assert item["category"] == source["category"]
            assert "coordinates" not in item
            assert item["collection_status"] in {"sourced", "needs_collection", "enriched"}
            themes = [fact["theme"] for fact in item["visitor_facts"]]
            assert "best-time" in themes
            assert "suggested-duration" in themes
            for fact in item["visitor_facts"]:
                assert fact["basis"] in ALLOWED_BASES
                assert len(fact["text"]) >= 10
            if item["collection_status"] == "enriched":
                assert any(fact["basis"] == "cited-source" for fact in item["visitor_facts"])
            elif item["collection_status"] == "sourced":
                assert any(fact["basis"] == "catalog-record" for fact in item["visitor_facts"])
            else:
                assert not any(
                    fact["basis"] in {"catalog-record", "cited-source"} for fact in item["visitor_facts"]
                )
            seen += 1
    assert seen == coverage["total_places"]
    assert coverage["total_places"] >= 40000
    gaps = json.loads((ROOT / "data" / "gaps.json").read_text(encoding="utf-8"))
    assert gaps["place_count"] == seen
    assert gaps["next_collection_prompt"]
