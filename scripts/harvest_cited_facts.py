#!/usr/bin/env python3
"""Attach cited visitor facts to existing places and add verified missing ones.

Facts are paraphrased from official tourism pages or from Wikidata claims.
Wikipedia article prose is not copied. Coordinates are taken only from
Wikidata, and only when they fall inside the target state. A conflicting
district is recorded as a flag; the catalog state is not changed.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import extract_places as ep

ROOT = ep.ROOT
PLACES_DIR = ep.DATA_DIR
OVERLAY_DIR = ROOT / "data" / "enrichment-overlay"
COVERAGE_PATH = ROOT / "data" / "coverage-summary.json"
GAPS_PATH = ROOT / "data" / "gaps.json"
USER_AGENT = ep.USER_AGENT

TARGET_STATES = (
    "Meghalaya",
    "Nagaland",
    "Tripura",
    "Mizoram",
)

# south, north, west, east
BBOX = {
    "Meghalaya": (25.02, 26.13, 89.80, 92.80),
    "Nagaland": (25.20, 27.05, 93.30, 95.25),
    "Tripura": (22.90, 24.55, 91.10, 92.40),
    "Mizoram": (21.95, 24.55, 92.15, 93.50),
}

GENERIC = {
    "fortress",
    "stupa",
    "tank",
    "hills",
    "river",
    "peak",
    "lake",
    "falls",
    "cave",
    "church",
    "memorial",
    "temple",
    "bridge",
    "park",
    "museum",
}

# Paraphrased from pages fetched for this harvest. Each text stays under 240 characters.
CURATED: dict[str, list[dict]] = {
    "mawlynnong-meghalaya": [
        {
            "theme": "local-culture",
            "text": "Meghalaya Tourism calls Mawlynnong Asia's cleanest village and God's Own Garden. It sits in East Khasi Hills, about 76 km from Shillong, near the Bangladesh border.",
            "source": "https://www.meghalayatourism.in/explore/destinations/by-region/khasi-hills/mawlynnong/",
        },
        {
            "theme": "history",
            "text": "The Nohwet living-root bridge is woven from Ficus elastica roots over generations, a Khasi practice the state tourism guide highlights in the village.",
            "source": "https://www.meghalayatourism.in/explore/destinations/by-region/khasi-hills/mawlynnong/",
        },
        {
            "theme": "access",
            "text": "Shared sumos leave Shillong for Pynursla; local cabs cover the last stretch. The state guide puts Shillong Airport about 103 km away.",
            "source": "https://www.meghalayatourism.in/explore/destinations/by-region/khasi-hills/mawlynnong/",
        },
        {
            "theme": "best-time",
            "text": "The state tourism page says Mawlynnong can be visited year-round, with post-monsoon and winter easier for being outdoors.",
            "source": "https://www.meghalayatourism.in/explore/destinations/by-region/khasi-hills/mawlynnong/",
        },
        {
            "theme": "hidden-gem",
            "text": "A bamboo sky viewpoint in the village looks over the Bangladesh plains, a short walk from the single-decker root bridge.",
            "source": "https://www.meghalayatourism.in/explore/destinations/by-region/khasi-hills/mawlynnong/",
        },
    ],
    "church-of-the-epiphany-meghalaya": [
        {
            "theme": "history",
            "text": "Meghalaya Tourism describes the Church of the Epiphany at Mawlynnong as more than a century old, set among gardens in the village.",
            "source": "https://www.meghalayatourism.in/explore/destinations/by-region/khasi-hills/mawlynnong/",
        },
    ],
    "nongriat-meghalaya": [
        {
            "theme": "access",
            "text": "Meghalaya Tourism describes a 3 km walk of about 3,500 stone steps from the trailhead down to Nongriat's double-decker living-root bridge.",
            "source": "https://www.meghalayatourism.in/explore/destinations/",
        },
        {
            "theme": "suggested-duration",
            "text": "The same guide allows about another hour beyond the bridge to reach Rainbow Falls, so the outing is a full day on foot.",
            "source": "https://www.meghalayatourism.in/explore/destinations/",
        },
    ],
    "umshiang-double-decker-root-bridge-meghalaya": [
        {
            "theme": "history",
            "text": "State tourism presents the double-decker living-root bridge as the focus of the Nongriat walk, reached by roughly 3,500 stone steps.",
            "source": "https://www.meghalayatourism.in/explore/destinations/",
        },
    ],
    "kongthong-meghalaya": [
        {
            "theme": "local-culture",
            "text": "Meghalaya Tourism calls Kongthong the Whistling Village, where each person is given a unique whistled tune used as a name.",
            "source": "https://www.meghalayatourism.in/explore/destinations/",
        },
        {
            "theme": "food",
            "text": "The state tourism board lists an organic-honey experience among visits to Kongthong.",
            "source": "https://www.meghalayatourism.in/experiences/curated-experiences/",
        },
    ],
    "mawsynram-meghalaya": [
        {
            "theme": "detail",
            "text": "Meghalaya Tourism describes Mawsynram, in the East Khasi Hills, as the wettest place on Earth, with nearly 12,000 mm of rain a year.",
            "source": "https://www.meghalayatourism.in/",
        },
    ],
    "mawphanlur-meghalaya": [
        {
            "theme": "hidden-gem",
            "text": "State tourism promotes Mawphanlur for night-sky views from a village on open rolling hills in the Khasi Hills.",
            "source": "https://www.meghalayatourism.in/explore/destinations/",
        },
    ],
    "nohkalikai-falls-meghalaya": [
        {
            "theme": "detail",
            "text": "Meghalaya Tourism singles out Nohkalikai's plunge as one of the waterfalls Sohra is known for, in forest above the plains.",
            "source": "https://www.meghalayatourism.in/explore/destinations/",
        },
    ],
    "dainthlen-falls-meghalaya": [
        {
            "theme": "detail",
            "text": "The state destinations guide pairs Dainthlen's flow with Nohkalikai among the waterfalls that define Sohra.",
            "source": "https://www.meghalayatourism.in/explore/destinations/",
        },
    ],
    "mawsmai-cave-meghalaya": [
        {
            "theme": "access",
            "text": "Meghalaya Tourism describes Mawsmai Cave, near Sohra, as a short limestone cave with narrow squeezes rather than a technical caving trip.",
            "source": "https://www.meghalayatourism.in/explore/destinations/",
        },
    ],
    "rangthylliang-1-root-bridge-meghalaya": [
        {
            "theme": "local-culture",
            "text": "Meghalaya Tourism lists Rangthylliang among its living-root-bridge experiences.",
            "source": "https://www.meghalayatourism.in/experiences/curated-experiences/",
        },
    ],
    "dawki-meghalaya": [
        {
            "theme": "detail",
            "text": "Meghalaya Tourism describes Dawki's Umngot River as clear enough for boating, on the border with Bangladesh.",
            "source": "https://rc-www.meghalayatourism.in/mawlynnong-dawki/",
        },
        {
            "theme": "placement-flag",
            "text": "A state tourism page places Dawki in West Jaintia Hills. The catalog fact still says Jaintia Hills district, and that original placement is kept.",
            "source": "https://rc-www.meghalayatourism.in/mawlynnong-dawki/",
        },
    ],
    "chandigre-meghalaya": [
        {
            "theme": "hidden-gem",
            "text": "Meghalaya Tourism lists Chandigre village among its curated Garo Hills experiences.",
            "source": "https://www.meghalayatourism.in/experiences/curated-experiences/",
        },
    ],
    "siju-cave-meghalaya": [
        {
            "theme": "hidden-gem",
            "text": "State tourism bills Siju as a Garo Hills stop, describing it as a place that feels frozen in time.",
            "source": "https://www.meghalayatourism.in/experiences/curated-experiences/",
        },
    ],
    "balpakram-national-park-meghalaya": [
        {
            "theme": "local-culture",
            "text": "Meghalaya Tourism groups Balpakram National Park with Garo Hills journeys and lists it as its own guided experience.",
            "source": "https://www.meghalayatourism.in/experiences/curated-experiences/",
        },
    ],
    "dzukou-valley-nagaland": [
        {
            "theme": "detail",
            "text": "Nagaland Tourism places Dzukou Valley at about 2,452 m, with summer meadows, the Dzukou lily, bamboo, streams, and caves.",
            "source": "https://tourism.nagaland.gov.in/where-the-clouds-rest-discovering-the-magic-of-dzukou-valley/",
        },
        {
            "theme": "placement-flag",
            "text": "The state tourism article says the valley lies between Nagaland and Manipur. The catalog keeps the Nagaland record and its Viswema fact.",
            "source": "https://tourism.nagaland.gov.in/where-the-clouds-rest-discovering-the-magic-of-dzukou-valley/",
        },
        {
            "theme": "best-time",
            "text": "The state write-up highlights summer, when the valley flowers, as the season the meadows are known for.",
            "source": "https://tourism.nagaland.gov.in/where-the-clouds-rest-discovering-the-magic-of-dzukou-valley/",
        },
    ],
    "khonoma-nature-conservation-and-tragopan-sanctuary-nagaland": [
        {
            "theme": "history",
            "text": "Nagaland Tourism says the Khonoma Nature Conservation and Tragopan Sanctuary was set up in 1998 to protect Blyth's tragopan.",
            "source": "https://tourism.nagaland.gov.in/khonoma-village/",
        },
        {
            "theme": "local-culture",
            "text": "The same page calls Khonoma a warrior village about 20 km from Kohima and the first Green Village in Asia.",
            "source": "https://tourism.nagaland.gov.in/khonoma-village/",
        },
    ],
    "khonoma-nagaland": [
        {
            "theme": "history",
            "text": "Nagaland Tourism calls Khonoma a warrior village about 20 km from Kohima, known for resistance in the colonial period.",
            "source": "https://tourism.nagaland.gov.in/khonoma-village/",
        },
        {
            "theme": "local-culture",
            "text": "The state page says Khonoma was described as Asia's first Green Village, and that its tragopan sanctuary was set up in 1998.",
            "source": "https://tourism.nagaland.gov.in/khonoma-village/",
        },
    ],
    "kohima-war-cemetery-nagaland": [
        {
            "theme": "history",
            "text": "Nagaland Tourism describes Kohima War Cemetery as the memorial for soldiers killed in the Second World War Battle of Kohima, also called the Battle of the Tennis Court.",
            "source": "https://tourism.nagaland.gov.in/",
        },
        {
            "theme": "access",
            "text": "The state tourism guide places the cemetery in Kohima district, in landscaped gardens maintained as a place of remembrance.",
            "source": "https://tourism.nagaland.gov.in/",
        },
    ],
    "ujjayanta-palace-tripura": [
        {
            "theme": "history",
            "text": "Tripura Tourism says Maharaja Radha Kishore Manikya built Ujjayanta Palace in 1901, and that Rabindranath Tagore gave the palace its name.",
            "source": "https://tripuratourism.gov.in/single-tour.php?id=1",
        },
        {
            "theme": "detail",
            "text": "The state page describes three domes about 86 feet high, Mughal-style gardens, and a museum in the palace after the assembly moved out in 2011.",
            "source": "https://tripuratourism.gov.in/single-tour.php?id=1",
        },
        {
            "theme": "access",
            "text": "Tripura Tourism places the palace in Agartala, West Tripura, in the heart of the city.",
            "source": "https://tripuratourism.gov.in/single-tour.php?id=1",
        },
    ],
    "unakoti-tripura": [
        {
            "theme": "history",
            "text": "Tripura Tourism calls Unakoti a Shaiva pilgrimage with rock carvings dated to the 7th to 9th centuries, including a Shiva head about 30 feet high.",
            "source": "https://tripuratourism.gov.in/single-tour.php?id=3",
        },
        {
            "theme": "festival",
            "text": "The state page says the Ashokastami Mela at Unakoti draws thousands of pilgrims each April.",
            "source": "https://tripuratourism.gov.in/single-tour.php?id=3",
        },
        {
            "theme": "access",
            "text": "The tourism page puts Unakoti 178 km from Agartala and 8 km from Kailashahar, reached via Kumarghat.",
            "source": "https://tripuratourism.gov.in/single-tour.php?id=3",
        },
        {
            "theme": "placement-flag",
            "text": "The state page calls Kailashahar the headquarters of North Tripura. The catalog fact already says Unakoti district, and that placement is kept.",
            "source": "https://tripuratourism.gov.in/single-tour.php?id=3",
        },
    ],
    "neermahal-tripura": [
        {
            "theme": "history",
            "text": "Tripura Tourism says Maharaja Bir Bikram Kishore Manikya built Neermahal in 1930 as a summer palace in Rudrasagar Lake.",
            "source": "https://tripuratourism.gov.in/single-tour.php?id=8",
        },
        {
            "theme": "access",
            "text": "The state page places Neermahal at Melaghar in Sepahijala district, 53 km south of Agartala, and reached by boat.",
            "source": "https://tripuratourism.gov.in/single-tour.php?id=8",
        },
        {
            "theme": "festival",
            "text": "A boat festival is held on Rudrasagar in July or August, according to the state tourism page.",
            "source": "https://tripuratourism.gov.in/single-tour.php?id=8",
        },
    ],
    "rudrasagar-lake-tripura": [
        {
            "theme": "detail",
            "text": "Tripura Tourism says Rudrasagar covers about 5.3 square km and hosts resident and migratory birds, with boating beside Neermahal.",
            "source": "https://tripuratourism.gov.in/single-tour.php?id=8",
        },
        {
            "theme": "festival",
            "text": "The same page says a boat festival is held on the lake in July or August.",
            "source": "https://tripuratourism.gov.in/single-tour.php?id=8",
        },
    ],
    "laitlum-canyon-meghalaya": [
        {
            "theme": "detail",
            "text": "Meghalaya Tourism lists Laitlum Canyon under the Khasi Hills, as a ridge-and-gorge viewpoint.",
            "source": "https://www.meghalayatourism.in/explore/destinations/",
        },
    ],
    "hornbill-festival-nagaland": [
        {
            "theme": "festival",
            "text": "Nagaland Tourism dates the Hornbill Festival to 2000. It runs ten days and is promoted as the Festival of Festivals.",
            "source": "https://tourism.nagaland.gov.in/events/hornbill-festival/",
        },
        {
            "theme": "food",
            "text": "The official event list includes a local-cuisine food festival plus Naga king-chilli and pineapple eating contests.",
            "source": "https://tourism.nagaland.gov.in/events/hornbill-festival/",
        },
        {
            "theme": "best-time",
            "text": "The state tourism calendar lists the Hornbill Festival for 1-10 December.",
            "source": "https://tourism.nagaland.gov.in/",
        },
    ],
}

CANDIDATES = [
    ("Shillong", "Meghalaya", "hill-station", ["hill-station"]),
    ("Shillong Peak", "Meghalaya", "nature", ["peak"]),
    ("Don Bosco Centre for Indigenous Cultures", "Meghalaya", "heritage", ["museum"]),
    ("Laitlum Canyon", "Meghalaya", "nature", ["canyon"]),
    ("Mawphlang Sacred Forest", "Meghalaya", "nature", ["sacred-grove"]),
    ("Kyllang Rock", "Meghalaya", "nature", ["rock"]),
    ("Shnongpdeng", "Meghalaya", "offbeat", ["village"]),
    ("Kohima War Cemetery", "Nagaland", "heritage", ["war-cemetery"]),
    ("Kisama Heritage Village", "Nagaland", "heritage", ["festival-ground"]),
    ("Khonoma", "Nagaland", "offbeat", ["village"]),
]


def api_get(base: str, params: dict[str, str]) -> dict:
    params = {**params, "format": "json"}
    url = base + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.load(response)


def in_bbox(lat: float, lon: float, state: str) -> bool:
    south, north, west, east = BBOX[state]
    return south <= lat <= north and west <= lon <= east


def needs_tight_match(name: str) -> bool:
    tokens = [part for part in re.split(r"[^A-Za-z0-9]+", name) if part]
    return len(tokens) <= 2 and tokens[0].lower() in GENERIC


def haversine_deg(lat: float, lon: float, other_lat: float, other_lon: float) -> float:
    return ((lat - other_lat) ** 2 + (lon - other_lon) ** 2) ** 0.5


def claim_time(value: dict) -> str | None:
    raw = str(value.get("time") or "")
    match = re.match(r"^[+-]0*(\d+)-(\d{2})-(\d{2})", raw)
    if not match:
        return None
    year = int(match.group(1))
    if year < 1 or year > 2100:
        return None
    return str(year)


def entity_label(entity: dict) -> str:
    labels = entity.get("labels") or {}
    eng = labels.get("en") or {}
    return (eng.get("value") or "").strip()


def admin_state_and_district(entity: dict, cache: dict[str, dict]) -> tuple[str | None, str | None]:
    states, district = admin_states_and_district(entity, cache)
    return (next(iter(states), None), district)


def admin_states_and_district(entity: dict, cache: dict[str, dict]) -> tuple[set[str], str | None]:
    states: set[str] = set()
    district = None
    for claim in (entity.get("claims") or {}).get("P131") or []:
        mainsnak = claim.get("mainsnak") or {}
        datavalue = (mainsnak.get("datavalue") or {}).get("value") or {}
        qid = datavalue.get("id")
        if not qid:
            continue
        seen = {entity.get("id")}
        current = qid
        for _ in range(6):
            if current in ep.STATE_QIDS:
                states.add(ep.STATE_QIDS[current])
                break
            parent = cache.get(current)
            if parent is None:
                break
            label = entity_label(parent)
            if label and re.search(r"district", label, re.I) and district is None:
                district = label
            parents = (parent.get("claims") or {}).get("P131") or []
            next_id = None
            for parent_claim in parents:
                value = ((parent_claim.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {}
                next_id = value.get("id")
                if next_id:
                    break
            if not next_id or next_id in seen:
                break
            seen.add(next_id)
            current = next_id
    return states, district


def coords_of(entity: dict) -> tuple[float, float] | None:
    claims = (entity.get("claims") or {}).get("P625") or []
    if not claims:
        return None
    value = ((claims[0].get("mainsnak") or {}).get("datavalue") or {}).get("value") or {}
    if "latitude" not in value or "longitude" not in value:
        return None
    return float(value["latitude"]), float(value["longitude"])


def fetch_entities(qids: list[str]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    pending = [qid for qid in qids if qid]
    while pending:
        batch = pending[:40]
        pending = pending[40:]
        data = api_get(
            "https://www.wikidata.org/w/api.php",
            {
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "labels|descriptions|claims",
                "languages": "en",
            },
        )
        entities = data.get("entities") or {}
        found.update(entities)
        extra = []
        for entity in entities.values():
            for claim in (entity.get("claims") or {}).get("P131") or []:
                value = ((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {}
                parent = value.get("id")
                if parent and parent not in found and parent not in extra and parent not in ep.STATE_QIDS:
                    extra.append(parent)
        pending.extend(extra)
        time.sleep(0.2)
    return found


def wiki_candidates(name: str, state: str) -> list[dict]:
    data = api_get(
        "https://en.wikipedia.org/w/api.php",
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": f"{name} {state}",
            "gsrlimit": "4",
            "prop": "pageprops|coordinates|description|pageimages",
            "ppprop": "wikibase_item",
            "piprop": "name",
            "redirects": "1",
        },
    )
    pages = (data.get("query") or {}).get("pages") or {}
    rows = []
    for page in pages.values():
        qid = (page.get("pageprops") or {}).get("wikibase_item")
        if not qid:
            continue
        coords = page.get("coordinates") or []
        point = None
        if coords:
            point = (float(coords[0]["lat"]), float(coords[0]["lon"]))
        rows.append(
            {
                "title": page.get("title") or "",
                "qid": qid,
                "description": page.get("description") or "",
                "point": point,
                "image": (page.get("pageimage") or "").replace(" ", "_"),
            }
        )
    return rows


def pick_match(name: str, state: str, place_point: tuple[float, float] | None, rows: list[dict]) -> dict | None:
    tight = needs_tight_match(name)
    limit = 0.12 if tight else 0.35
    best = None
    best_distance = 999.0
    folded = ep.slug(name)
    for row in rows:
        title = row["title"]
        if title.startswith("List of ") or title.startswith("Category:"):
            continue
        point = row["point"]
        if place_point and point:
            distance = haversine_deg(place_point[0], place_point[1], point[0], point[1])
            if distance <= limit and distance < best_distance:
                best = row
                best_distance = distance
            continue
        if place_point:
            continue
        title_slug = ep.slug(title)
        described = state.lower() in row["description"].lower() or state.lower() in title.lower()
        if described and (title_slug == folded or title_slug.startswith(folded)):
            return row
    return best


def wikidata_facts(entity: dict) -> list[str]:
    facts = []
    claims = entity.get("claims") or {}
    opened = claims.get("P571") or []
    if opened:
        when = claim_time((opened[0].get("mainsnak") or {}).get("datavalue", {}).get("value") or {})
        if when:
            facts.append(f"Wikidata records a start or opening year of {when} for this place.")
    descriptions = entity.get("descriptions") or {}
    summary = ((descriptions.get("en") or {}).get("value") or "").strip()
    if summary and len(summary) >= 12:
        sentence = f"Wikidata's short description is: {summary}."
        if len(sentence) <= 240:
            facts.append(sentence)
    return facts[:3]


def commons_page(filename: str) -> str | None:
    if not filename:
        return None
    return "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(filename)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ensure_list(item: dict, key: str) -> list:
    item.setdefault(key, [])
    return item[key]


def add_cited(item: dict, theme: str, text: str, source: str) -> bool:
    if len(text) < 10 or len(text) > 240:
        return False
    facts = ensure_list(item, "visitor_facts")
    if any(existing.get("text") == text for existing in facts):
        return False
    facts.append({"theme": theme, "text": text, "basis": "cited-source", "source": source})
    sources = ensure_list(item, "sources")
    if not any(entry.get("url") == source for entry in sources):
        sources.append({"url": source, "publisher": urllib.parse.urlparse(source).netloc})
    item["collection_status"] = "enriched"
    return True


def add_photo(item: dict, page_url: str, title: str) -> None:
    photos = ensure_list(item, "photos")
    if any(photo.get("page_url") == page_url for photo in photos):
        return
    photos.append(
        {
            "page_url": page_url,
            "title": title,
            "source": "Wikimedia Commons",
            "note": "Open the file page for the license and author. The image file is not stored here.",
        }
    )


def refresh_missing(item: dict) -> None:
    themes = {fact.get("theme") for fact in item.get("visitor_facts") or []}
    cited_best = any(
        fact.get("theme") == "best-time" and fact.get("basis") == "cited-source"
        for fact in item.get("visitor_facts") or []
    )
    missing = []
    for theme, gap in (
        ("history", "history"),
        ("festival", "festival"),
        ("local-culture", "local-culture"),
        ("food", "food"),
        ("access", "access"),
    ):
        if theme not in themes:
            missing.append(gap)
    if not cited_best:
        missing.append("place-specific-season")
    if not item.get("district"):
        missing.append("district")
    item["missing_themes"] = missing


def apply_curated(overlay: list[dict]) -> int:
    by_id = {item["id"]: item for item in overlay}
    added = 0
    for place_id, facts in CURATED.items():
        item = by_id.get(place_id)
        if item is None:
            print(f"  curated skip, id not in catalog: {place_id}", flush=True)
            continue
        for fact in facts:
            if add_cited(item, fact["theme"], fact["text"], fact["source"]):
                added += 1
        refresh_missing(item)
    return added


def harvest_existing(state: str, records: list[dict], overlay: list[dict]) -> int:
    by_id = {item["id"]: item for item in overlay}
    added = 0
    for index, record in enumerate(records, start=1):
        item = by_id[record["id"]]
        point = None
        if record.get("coordinates"):
            point = (record["coordinates"]["lat"], record["coordinates"]["lon"])
        try:
            rows = wiki_candidates(record["name"], state)
        except Exception as exc:  # noqa: BLE001
            print(f"  search failed for {record['name']}: {exc}", flush=True)
            continue
        match = pick_match(record["name"], state, point, rows)
        if match:
            entities = fetch_entities([match["qid"]])
            entity = entities.get(match["qid"]) or {}
            wiki_state, district = admin_state_and_district(entity, entities)
            if wiki_state and wiki_state != state:
                note = (
                    f"Wikidata links a page titled {match['title']} to {wiki_state}. "
                    f"The catalog keeps this record in {state}."
                )
                if add_cited(item, "placement-flag", note, f"https://www.wikidata.org/wiki/{match['qid']}"):
                    added += 1
            else:
                for text in wikidata_facts(entity):
                    if add_cited(item, "detail", text, f"https://www.wikidata.org/wiki/{match['qid']}"):
                        added += 1
                if district and wiki_state == state:
                    current = item.get("district")
                    if not current:
                        item["district"] = district
                        item["district_fact_state"] = state
                    elif district.lower() not in current.lower() and current.lower() not in district.lower():
                        flag = (
                            f"Wikidata names {district}. The catalog already records {current}, "
                            "and that original area is kept."
                        )
                        if add_cited(
                            item,
                            "placement-flag",
                            flag,
                            f"https://www.wikidata.org/wiki/{match['qid']}",
                        ):
                            added += 1
                image = match["image"]
                claims = (entity.get("claims") or {}).get("P18") or []
                if claims and not image:
                    image = ((claims[0].get("mainsnak") or {}).get("datavalue") or {}).get("value") or ""
                page = commons_page(image)
                if page:
                    add_photo(item, page, image)
                    if add_cited(
                        item,
                        "photo",
                        f"A Wikimedia Commons file, {image.replace('_', ' ')}, is linked from the matched page.",
                        page,
                    ):
                        added += 1
        refresh_missing(item)
        if index % 12 == 0:
            print(f"  {state}: reviewed {index}/{len(records)}", flush=True)
        time.sleep(0.15)
    return added


def search_wikidata(name: str, state: str) -> list[str]:
    found: list[str] = []
    for query in (name, f"{name} {state}"):
        data = api_get(
            "https://www.wikidata.org/w/api.php",
            {
                "action": "wbsearchentities",
                "search": query,
                "language": "en",
                "limit": "5",
            },
        )
        for row in data.get("search") or []:
            if row["id"] not in found:
                found.append(row["id"])
        if found:
            return found
        time.sleep(0.15)
    return found


def add_verified_places(existing: dict[str, list[dict]]) -> list[str]:
    created = []
    for name, state, category, tags in CANDIDATES:
        records = existing[state]
        if any(ep.slug(record["name"]) == ep.slug(name) for record in records):
            print(f"  already present: {name}, {state}", flush=True)
            continue
        qids = search_wikidata(name, state)
        time.sleep(0.2)
        if not qids:
            print(f"  no Wikidata hit: {name}", flush=True)
            continue
        entities = fetch_entities(qids[:3])
        chosen = None
        chosen_state = None
        chosen_district = None
        for qid in qids[:3]:
            entity = entities.get(qid) or {}
            label = entity_label(entity) or ""
            if ep.slug(label) != ep.slug(name):
                continue
            states, district = admin_states_and_district(entity, entities)
            point = coords_of(entity)
            summary = ((entity.get("descriptions") or {}).get("en") or {}).get("value") or ""
            described_here = state.lower() in summary.lower() or state.lower() in label.lower()
            if state not in states and not (described_here and point and in_bbox(point[0], point[1], state)):
                continue
            if point and not in_bbox(point[0], point[1], state):
                print(f"  rejected {name}: coordinates outside {state}", flush=True)
                continue
            if point is None and needs_tight_match(name):
                continue
            chosen = entity
            chosen_state = state
            chosen_district = district
            if states - {state}:
                chosen["harvest_flags"] = sorted(states - {state})
            break
        if not chosen or chosen_state != state:
            print(f"  unverified, not added: {name}, {state}", flush=True)
            continue
        point = coords_of(chosen)
        description = f"{name} is a {category.replace('-', ' ')} place in {state}, India."
        facts = ["Included from Wikidata after the administrative chain matched this state."]
        if chosen_district:
            fact = f"Lies in {chosen_district}, {state}."
            if 10 <= len(fact) <= 240:
                facts.append(fact)
        summary = ((chosen.get("descriptions") or {}).get("en") or {}).get("value")
        if summary:
            sentence = f"Wikidata's short description is: {summary}."
            if 10 <= len(sentence) <= 240:
                facts.append(sentence)
        other_states = chosen.get("harvest_flags") or []
        if other_states:
            flag = (
                f"Wikidata also names {', '.join(other_states)} in an administrative statement. "
                f"The English description and coordinates support {state}, so the record stays there."
            )
            if len(flag) <= 240:
                facts.append(flag)
        used = {record["id"] for record in records}
        record = {
            "id": ep.unique_id(name, state, chosen.get("id"), used),
            "name": name,
            "state": state,
            "category": category,
            "description": description,
            "facts": facts[:6],
            "tags": ["lesser-known", *tags],
        }
        if point and ep.in_india(point[0], point[1]):
            record["coordinates"] = {"lat": round(point[0], 5), "lon": round(point[1], 5)}
        records.append(record)
        created.append(f"{name} ({state})")
        print(f"  added {name} in {state}", flush=True)
    return created


def overlay_stub(record: dict) -> dict:
    from build_catalog_overlay import best_time, suggested_duration

    item = {
        "id": record["id"],
        "name": record["name"],
        "state": record["state"],
        "category": record["category"],
        "district": None,
        "district_fact_state": None,
        "district_state_conflict": False,
        "visitor_facts": [
            {
                "theme": "detail",
                "text": fact,
                "basis": "catalog-record",
            }
            for fact in record.get("facts") or []
            if not fact.startswith("Included from Wikidata")
        ] + [
            {
                "theme": "detail",
                "text": "Added after Wikidata's administrative chain matched the catalog state. Visitor detail beyond that is still open.",
                "basis": "cited-source",
                "source": "https://www.wikidata.org/",
            },
            {
                "theme": "best-time",
                "text": best_time(record["state"], record["category"], set(record.get("tags") or [])),
                "basis": "regional-climate",
            },
            {
                "theme": "suggested-duration",
                "text": suggested_duration(record["category"], set(record.get("tags") or []), None),
                "basis": "category-planning",
            },
        ],
        "missing_themes": ["history", "festival", "local-culture", "food", "access", "place-specific-season"],
        "collection_status": "enriched",
        "sources": [{"url": "https://www.wikidata.org/", "publisher": "www.wikidata.org"}],
    }
    refresh_missing(item)
    return item


def ensure_visit_guidance(overlay: list[dict]) -> None:
    from build_catalog_overlay import best_time, suggested_duration

    for item in overlay:
        themes = {fact.get("theme") for fact in item.get("visitor_facts") or []}
        tags = set()
        if "best-time" not in themes:
            item["visitor_facts"].append(
                {
                    "theme": "best-time",
                    "text": best_time(item["state"], item["category"], tags),
                    "basis": "regional-climate",
                }
            )
        if "suggested-duration" not in themes:
            item["visitor_facts"].append(
                {
                    "theme": "suggested-duration",
                    "text": suggested_duration(item["category"], tags, None),
                    "basis": "category-planning",
                }
            )
        refresh_missing(item)


def refresh_reports() -> None:
    coverage = load_json(COVERAGE_PATH)
    gaps = load_json(GAPS_PATH)
    missing: dict[str, int] = {}
    enriched = 0
    total = 0
    by_state = {row["state"]: row for row in coverage["states"]}
    for path in sorted(PLACES_DIR.glob("*.json")):
        places = load_json(path)
        overlay = load_json(OVERLAY_DIR / path.name)
        state = places[0]["state"] if places else path.stem
        row = by_state.get(state)
        state_enriched = sum(1 for item in overlay if item.get("collection_status") == "enriched")
        if row is not None:
            row["enriched_places"] = state_enriched
            row["overlay_places"] = len(overlay)
        enriched += state_enriched
        total += len(places)
        for item in overlay:
            for theme in item.get("missing_themes") or []:
                missing[theme] = missing.get(theme, 0) + 1
    coverage["total_places"] = total
    coverage["enriched_places"] = enriched
    coverage["enriched_percent"] = round(100 * enriched / total, 1) if total else 0
    dump_json(COVERAGE_PATH, coverage)
    gaps["place_count"] = total
    gaps["enriched_places"] = enriched
    gaps["enriched_percent"] = coverage["enriched_percent"]
    gaps["missing_theme_counts"] = dict(sorted(missing.items(), key=lambda item: -item[1]))
    gaps["harvest_note"] = (
        f"Cited harvest covered {', '.join(TARGET_STATES)}. "
        f"{enriched} places now have at least one cited visitor fact."
    )
    dump_json(GAPS_PATH, gaps)


def main() -> int:
    candidates_only = "--candidates-only" in sys.argv
    bundles = {}
    for state in TARGET_STATES:
        path = PLACES_DIR / f"{ep.slug(state)}.json"
        records = load_json(path)
        overlay_path = OVERLAY_DIR / path.name
        overlay = load_json(overlay_path)
        print(f"{state}: {len(records)} places", flush=True)
        curated = apply_curated(overlay)
        print(f"  curated facts added: {curated}", flush=True)
        if not candidates_only:
            harvested = harvest_existing(state, records, overlay)
            print(f"  wikidata/commons facts added: {harvested}", flush=True)
        ensure_visit_guidance(overlay)
        bundles[state] = (path, records, overlay_path, overlay)

    print("Checking candidate places", flush=True)
    existing = {state: bundles[state][1] for state in TARGET_STATES}
    created = add_verified_places(existing)
    for name_state in created:
        state = name_state.rsplit(" (", 1)[1].rstrip(")")
        name = name_state.rsplit(" (", 1)[0]
        records = bundles[state][1]
        overlay = bundles[state][3]
        record = next(item for item in records if item["name"] == name)
        if not any(item["id"] == record["id"] for item in overlay):
            overlay.append(overlay_stub(record))

    for state, (path, records, overlay_path, overlay) in bundles.items():
        records.sort(key=lambda record: record["id"])
        overlay.sort(key=lambda item: item["id"])
        dump_json(path, records)
        dump_json(overlay_path, overlay)
        enriched = sum(1 for item in overlay if item.get("collection_status") == "enriched")
        print(f"{state} status: {enriched}/{len(overlay)} enriched, {len(created)} new places this session", flush=True)

    refresh_reports()
    print(f"New places: {created or 'none'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
