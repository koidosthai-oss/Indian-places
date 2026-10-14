#!/usr/bin/env python3
"""Coverage summary, visitor overlay, and collection gaps for every place.

The overlay does not add places or coordinates. Visitor lines that are not
already in a catalog record are marked with a basis of regional-climate or
category-planning. District text is copied from existing facts and is never
used to move a place into another state.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACES_DIR = ROOT / "data" / "places"
OVERLAY_DIR = ROOT / "data" / "enrichment-overlay"
COVERAGE_PATH = ROOT / "data" / "coverage-summary.json"
GAPS_PATH = ROOT / "data" / "gaps.json"

BOILERPLATE_PREFIXES = (
    "Known as a ",
    "Listed in ",
    "Included because mapped ",
)

HISTORY_PREFIXES = (
    "Dates from ",
    "Opened in ",
    "Recognised as ",
    "Built in the ",
    "Architect: ",
    "Founded by ",
    "Created by ",
    "Named after ",
    "Maintained under ",
    "About ",
)
SETTING_PREFIXES = (
    "Covers about ",
    "Rises about ",
    "Stands at about ",
    "Mapped elevation ",
)
CULTURE_PREFIXES = (
    "Dedicated to ",
    "Associated with ",
    "Part of ",
    "Set beside ",
    "Set on ",
)
FESTIVAL_RE = re.compile(
    r"\b(festival|mela|urs|jatra|pooram|carnival|theru)\b",
    re.I,
)
FOOD_RE = re.compile(
    r"\b(cuisine|food|dish|seafood|thali|sweetmeat|spice market)\b",
    re.I,
)
DISTRICT_RE = re.compile(r"^Lies in (.+), ([^,]+)\.?$")

WEST_COAST = {
    "Goa",
    "Maharashtra",
    "Karnataka",
    "Kerala",
    "Gujarat",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Lakshadweep",
}
BAY_NORTHEAST_MONSOON = {"Tamil Nadu", "Puducherry", "Andhra Pradesh"}
WEST_HIMALAYA = {"Himachal Pradesh", "Uttarakhand", "Jammu and Kashmir"}
EAST_HIMALAYA = {"Sikkim", "Arunachal Pradesh"}
NORTHEAST = {
    "Meghalaya",
    "Nagaland",
    "Manipur",
    "Mizoram",
    "Tripura",
    "Assam",
    "Sikkim",
    "Arunachal Pradesh",
}
WEST_GHATS = {"Maharashtra", "Goa", "Karnataka", "Kerala", "Tamil Nadu", "Gujarat"}

# States whose files are thin relative to how much travel writing already exists.
THIN_POTENTIAL = {
    "Arunachal Pradesh": "Hill circuits, high lakes, and village stays are barely represented.",
    "Meghalaya": "Living-root bridges, cave systems, and Khasi and Garo villages are sparse.",
    "Nagaland": "Hill villages, festivals, and district headquarters are barely represented.",
    "Manipur": "Loktak, hill villages, and valley sacred sites need another collection pass.",
    "Mizoram": "Hill towns, villages, and ridge viewpoints are sparse.",
    "Tripura": "Palaces, temples, and hill spots are sparse.",
    "Sikkim": "Monasteries, high lakes, and village trails need more named sites.",
    "Andaman and Nicobar Islands": "Beaches, islands, and forest trails beyond the main settlements are sparse.",
}


def percent(part: int, whole: int) -> float:
    if whole == 0:
        return 0.0
    return round(100 * part / whole, 1)


def is_boilerplate(fact: str) -> bool:
    return fact.startswith(BOILERPLATE_PREFIXES)


def theme_for(fact: str) -> str:
    if fact.startswith(SETTING_PREFIXES):
        return "setting"
    if fact.startswith("About ") and "visit" in fact.lower():
        return "detail"
    if fact.startswith(HISTORY_PREFIXES) or fact.startswith("Recognised as"):
        return "history"
    if fact.startswith(CULTURE_PREFIXES):
        return "local-culture"
    if FESTIVAL_RE.search(fact):
        return "festival"
    if FOOD_RE.search(fact):
        return "food"
    if fact.startswith("Lies in "):
        return "setting"
    return "detail"


def usable_area(area: str) -> bool:
    lowered = area.lower()
    return (
        len(area) >= 2
        and "|" not in area
        and "=" not in area
        and "address" not in lowered
        and "unknown" not in lowered
    )


def parse_district(facts: list[str], state: str) -> dict | None:
    for fact in facts:
        match = DISTRICT_RE.match(fact)
        if not match:
            continue
        area, fact_state = match.group(1).strip(), match.group(2).strip()
        return {
            "recorded_area": area if usable_area(area) else None,
            "recorded_state_in_fact": fact_state,
            "usable": usable_area(area),
            "state_conflict": fact_state != state,
            "fact": fact,
        }
    return None


def best_time(state: str, category: str, tags: set[str]) -> str:
    wildlife = category == "wildlife" or bool(tags & {"wildlife-sanctuary", "national-park", "zoo"})
    if wildlife:
        if state in NORTHEAST or state in EAST_HIMALAYA:
            return (
                "In the northeast, wildlife visits are usually planned from November to April, "
                "outside the heaviest rains. Confirm the named park's gate dates before travel."
            )
        if state == "Ladakh":
            return (
                "Ladakh's high parks and lakes are generally reachable from about June to September, "
                "when the passes are open."
            )
        return (
            "Many Indian wildlife reserves are open from November to June and close in the monsoon. "
            "Opening months differ by park, so check the named reserve."
        )
    if category == "beach" or "beach" in tags:
        if state in WEST_COAST:
            return (
                "Along the Arabian Sea, November to February is the usual calm, dry window. "
                "From about June to September the southwest monsoon brings heavy rain and rough surf."
            )
        if state == "Andaman and Nicobar Islands":
            return (
                "The Andaman and Nicobar coast is most often visited from November to April. "
                "May to September is wetter, with fewer boats between islands."
            )
        if state in BAY_NORTHEAST_MONSOON:
            return (
                "On this part of the Bay of Bengal coast, January to March is generally dry. "
                "October to December brings the northeast monsoon."
            )
        return (
            "On the Bay of Bengal coast, November to February is the usual dry window. "
            "June to September is the wetter, stormier season."
        )
    if state == "Ladakh":
        return (
            "Plan Ladakh travel from about June to September. "
            "High passes close in winter and can shut again after heavy snow."
        )
    if state in WEST_HIMALAYA:
        return (
            "In the western Himalaya, March to June and September to November are the clearer windows. "
            "July and August are wet, with landslide risk on hill roads, and high villages can be snowbound in winter."
        )
    if "waterfall" in tags and state in WEST_GHATS:
        return (
            "Western Ghats falls are fullest from about July to November. "
            "November to February is the easier season for paths and viewpoints."
        )
    if state in EAST_HIMALAYA or state in NORTHEAST:
        if "waterfall" in tags:
            return (
                "Northeast waterfalls are strongest in the monsoon, about June to September, "
                "and easier to approach from October to April."
            )
        return (
            "In these hills, October to April is the drier travel season. "
            "June to September is lush and often wet, with slippery roads."
        )
    if state == "Rajasthan":
        return (
            "In Rajasthan, October to March is the comfortable season for forts, towns, and desert travel. "
            "April to June is extremely hot."
        )
    if category == "spiritual":
        return (
            "Shrines are visited year-round. October to March is the easier season on the plains; "
            "hill shrines may be harder to reach in winter snow or monsoon rain."
        )
    if category == "heritage":
        return (
            "October to March is the most comfortable season across most of India for walking heritage sites. "
            "Summers are hot on the plains and in the desert."
        )
    return (
        "October to March is the broadly comfortable season in much of India. "
        "Hill roads and coasts have a shorter dry window, and monsoon months change the approach."
    )


def recorded_elevation(facts: list[str]) -> int | None:
    for fact in facts:
        if not any(token in fact.lower() for token in ("elevation", "stands at about")):
            continue
        match = re.search(r"([\d,]+)\s*m\b", fact)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def suggested_duration(category: str, tags: set[str], elevation: int | None) -> str:
    if elevation is not None and elevation >= 2000:
        return (
            f"The catalog records about {elevation:,} m, so treat this as an overnight stop "
            "rather than a quick trip from the plains."
        )
    if category == "wildlife" or tags & {"national-park", "wildlife-sanctuary"}:
        return "Allow at least half a day for the gate and one outing. A useful visit is often one or two nights."
    if category == "hill-station":
        return "A hill station usually deserves a night. A single viewpoint can be a one-hour stop."
    if tags & {"pass", "peak"}:
        return "A roadside pass is a short stop. A summit or high trail can take the whole day."
    if category == "beach" or "beach" in tags:
        return "The shore itself is a few hours. Stay overnight if the place is a beach village."
    if category == "heritage":
        return "Most forts, palaces, and museums take two to four hours. A ruined hill fort can take longer."
    if category == "spiritual":
        return "A shrine visit is often one to two hours, longer on a festival day."
    if tags & {"waterfall", "cave"}:
        return "A waterfall or cave is often a half-day trip once the approach road is counted."
    return "Plan a short visit until a more detailed account is collected."


def hidden_gem_text(tags: set[str]) -> str | None:
    if "mapped" in tags and "lesser-known" in tags:
        return (
            "Published visitor write-ups are scarce. The place is in the catalog because it is a named, "
            "mapped site rather than a stop on the usual itinerary."
        )
    if "lesser-known" in tags:
        return "The catalog marks this place lesser-known, so it is a candidate for a slower visit rather than a standard circuit."
    return None


def access_text(coordinates: dict | None) -> str | None:
    if not coordinates:
        return None
    lat = coordinates["lat"]
    lon = coordinates["lon"]
    return (
        f"The catalog already stores a search pin at {lat:.5f} N, {lon:.5f} E. "
        "Use that pin only as a start, and confirm the last mile on the ground."
    )


def description_kind(record: dict) -> str:
    description = record.get("description") or ""
    if "tourism place" in description:
        return "generic-tourism-place"
    if "is a protected monument" in description:
        return "protected-monument-template"
    if re.search(
        r" is a (temple|fort|lake|hill|mountain|waterfall|beach|village|palace|peak|forest|ridge) ",
        description,
    ):
        return "typed-template"
    return "specific"


def enrich(record: dict) -> dict:
    facts = list(record.get("facts") or [])
    tags = set(record.get("tags") or [])
    description = record.get("description") or ""
    text_blob = " ".join(facts + [description])
    district = parse_district(facts, record["state"])
    highlights = []
    for fact in facts:
        if is_boilerplate(fact) or fact.startswith("Lies in "):
            continue
        highlights.append({"theme": theme_for(fact), "text": fact, "basis": "catalog-record"})
    for sentence in [description, *facts]:
        if FESTIVAL_RE.search(sentence) and sentence not in {item["text"] for item in highlights}:
            highlights.append({"theme": "festival", "text": sentence, "basis": "catalog-record"})
        if FOOD_RE.search(sentence) and sentence not in {item["text"] for item in highlights}:
            highlights.append({"theme": "food", "text": sentence, "basis": "catalog-record"})

    visitor_facts = list(highlights)
    visitor_facts.append(
        {
            "theme": "best-time",
            "text": best_time(record["state"], record["category"], tags),
            "basis": "regional-climate",
        }
    )
    elevation = recorded_elevation(facts)
    duration_basis = "catalog-record" if elevation is not None and elevation >= 2000 else "category-planning"
    visitor_facts.append(
        {
            "theme": "suggested-duration",
            "text": suggested_duration(record["category"], tags, elevation),
            "basis": duration_basis,
        }
    )
    access = access_text(record.get("coordinates"))
    if access:
        visitor_facts.append({"theme": "access", "text": access, "basis": "catalog-coordinates"})
    character = hidden_gem_text(tags)
    if character:
        visitor_facts.append({"theme": "hidden-gem", "text": character, "basis": "catalog-tags"})

    present = {item["theme"] for item in visitor_facts}
    missing = []
    if "history" not in present:
        missing.append("history")
    if "festival" not in present:
        missing.append("festival")
    if "local-culture" not in present:
        missing.append("local-culture")
    if "food" not in present:
        missing.append("food")
    if "access" not in present:
        missing.append("access")
    missing.append("place-specific-season")
    if district is None or not district["usable"]:
        missing.append("district")

    sourced = any(item["basis"] == "catalog-record" for item in visitor_facts)
    return {
        "id": record["id"],
        "name": record["name"],
        "state": record["state"],
        "category": record["category"],
        "district": None if district is None else district["recorded_area"],
        "district_fact_state": None if district is None else district["recorded_state_in_fact"],
        "district_state_conflict": bool(district and district["state_conflict"]),
        "visitor_facts": visitor_facts,
        "missing_themes": missing,
        "collection_status": "sourced" if sourced else "needs_collection",
    }


def main() -> int:
    OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
    state_rows = []
    tag_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    district_counts: Counter[tuple[str, str]] = Counter()
    conflicts = []
    unusable_districts = 0
    total = 0
    with_coordinates = 0
    sourced = 0
    needs = 0
    missing_theme_counts: Counter[str] = Counter()
    description_kinds: Counter[str] = Counter()

    for path in sorted(PLACES_DIR.glob("*.json")):
        records = json.loads(path.read_text(encoding="utf-8"))
        overlay = []
        categories: Counter[str] = Counter()
        coords = 0
        generic_only = 0
        concrete = 0
        short_desc = 0
        missing_facts = 0
        missing_district = 0
        kinds: Counter[str] = Counter()
        for record in records:
            item = enrich(record)
            overlay.append(item)
            total += 1
            categories[record["category"]] += 1
            category_counts[record["category"]] += 1
            for tag in record.get("tags") or []:
                tag_counts[tag] += 1
            if record.get("coordinates"):
                coords += 1
                with_coordinates += 1
            facts = record.get("facts") or []
            if not facts:
                missing_facts += 1
            if item["collection_status"] == "sourced":
                concrete += 1
                sourced += 1
            else:
                generic_only += 1
                needs += 1
            if len(record.get("description") or "") < 40:
                short_desc += 1
            kind = description_kind(record)
            kinds[kind] += 1
            description_kinds[kind] += 1
            if item["district"]:
                district_counts[(record["state"], item["district"])] += 1
            else:
                missing_district += 1
                if item["district_fact_state"]:
                    unusable_districts += 1
            if item["district_state_conflict"] and len(conflicts) < 40:
                conflicts.append(
                    {
                        "id": record["id"],
                        "name": record["name"],
                        "catalog_state": record["state"],
                        "fact_state": item["district_fact_state"],
                        "recorded_area": item["district"],
                    }
                )
            for theme in item["missing_themes"]:
                missing_theme_counts[theme] += 1
        overlay.sort(key=lambda item: item["id"])
        out_path = OVERLAY_DIR / path.name
        out_path.write_text(json.dumps(overlay, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        notes = []
        if generic_only:
            notes.append(f"{generic_only} places have only boilerplate facts and need collected visitor detail.")
        if short_desc:
            notes.append(f"{short_desc} descriptions are shorter than 40 characters.")
        if kinds["generic-tourism-place"]:
            notes.append(f"{kinds['generic-tourism-place']} descriptions still say 'tourism place'.")
        if missing_district:
            notes.append(f"{missing_district} places have no usable district in their facts.")
        if missing_facts:
            notes.append(f"{missing_facts} places have no facts array.")
        row = {
            "state": records[0]["state"] if records else path.stem,
            "file": path.name,
            "places": len(records),
            "with_coordinates": coords,
            "coordinates_percent": percent(coords, len(records)),
            "categories": dict(sorted(categories.items())),
            "missing_facts": missing_facts,
            "generic_facts_only": generic_only,
            "concrete_sourced_facts": concrete,
            "short_descriptions": short_desc,
            "description_kinds": dict(sorted(kinds.items())),
            "missing_district": missing_district,
            "description_notes": notes,
        }
        state_rows.append(row)
        print(
            f"{row['state']}: {row['places']} places, "
            f"{row['coordinates_percent']}% with coordinates, "
            f"{concrete} sourced, {generic_only} need collection",
            flush=True,
        )

    state_rows.sort(key=lambda row: row["state"])
    coverage = {
        "total_places": total,
        "with_coordinates": with_coordinates,
        "coordinates_percent": percent(with_coordinates, total),
        "sourced_fact_places": sourced,
        "needs_collection_places": needs,
        "sourced_fact_percent": percent(sourced, total),
        "categories": dict(category_counts.most_common()),
        "states": state_rows,
    }
    COVERAGE_PATH.write_text(json.dumps(coverage, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    thin_states = []
    for row in state_rows:
        note = THIN_POTENTIAL.get(row["state"])
        if note and row["places"] < 250:
            thin_states.append({"state": row["state"], "places": row["places"], "why": note})

    under_categories = []
    for name in ("offbeat", "hill-station", "beach", "wildlife"):
        count = category_counts[name]
        under_categories.append(
            {
                "category": name,
                "places": count,
                "percent": percent(count, total),
                "note": "Many real sites of this kind are still filed as nature, spiritual, or heritage.",
            }
        )

    sparse_tags = [
        {"tag": tag, "places": count}
        for tag, count in tag_counts.most_common()
        if tag not in {"lesser-known", "mapped", "state-protected"} and count < 200
    ]
    sparse_districts = [
        {"state": state, "recorded_area": area, "places": count}
        for (state, area), count in district_counts.most_common()
        if count <= 2
    ]
    # Keep the gap file usable: the rarest named areas, capped.
    sparse_districts = sorted(sparse_districts, key=lambda item: (item["places"], item["state"], item["recorded_area"]))[:200]

    next_prompt = (
        "Continue the India tourism catalog. Do not add coordinates or move a place to a different state or district. "
        "Collect the next round from open geographic and heritage sources for the thin files first: "
        "Meghalaya, Nagaland, Mizoram, Tripura, Manipur, Arunachal Pradesh, Sikkim, and the Andaman and Nicobar Islands. "
        "Prioritize offbeat villages, lesser-known temples, small hill spots, cave and waterfall approaches, "
        "and wildlife-reserve edges that are named but still missing from data/places. "
        "For places already listed, fill only the missing themes in data/enrichment-overlay "
        "(history, festival, local culture, food, access, and a place-specific season) when a source states them. "
        "Leave a gap when a source does not. Skip hotels, stations, and unnamed spots."
    )
    gaps = {
        "place_count": total,
        "overlay_coverage_percent": 100.0,
        "sourced_fact_percent": percent(sourced, total),
        "needs_collection_places": needs,
        "needs_collection_percent": percent(needs, total),
        "missing_coordinates": total - with_coordinates,
        "unusable_district_facts": unusable_districts,
        "missing_theme_counts": dict(missing_theme_counts.most_common()),
        "thin_states": thin_states,
        "underrepresented_categories": under_categories,
        "sparse_tags": sparse_tags,
        "sparse_recorded_areas_sample": sparse_districts,
        "district_state_conflicts_sample": conflicts,
        "open_ended": (
            "The catalog is not finished. Another collection round should add named places "
            "and replace regional visit notes with place-specific facts when a source supports them."
        ),
        "next_collection_prompt": next_prompt,
    }
    GAPS_PATH.write_text(json.dumps(gaps, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Processed {total} places. Overlay coverage 100%. "
        f"Sourced facts {percent(sourced, total)}%. Need collection {needs}.",
        flush=True,
    )
    print(f"Wrote {COVERAGE_PATH}", flush=True)
    print(f"Wrote {GAPS_PATH}", flush=True)
    print(f"Wrote {OVERLAY_DIR}/ ({len(state_rows)} files)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
