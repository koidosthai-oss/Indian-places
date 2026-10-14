#!/usr/bin/env python3
"""Add mapped places that Wikipedia categories and list pages do not name.

Sources:
- GeoNames India dump (temples, shrines, forts, ruins, caves, falls, lakes,
  reservoirs, dunes, ridges, valleys, passes, peaks, hills, mountains,
  islands, beaches, ghats, and similar).
- Wikidata items in India with coordinates for temples, mosques, churches,
  monasteries, forts, palaces, waterfalls, caves, beaches, lakes, parks,
  museums, monuments, and archaeological sites.
- OpenStreetMap named tourism, historic, and natural features.

These are geographic records, including sites with little or no visitor
write-up. Article text is not copied. Run after scripts/extract_places.py:

    .venv/bin/python scripts/merge_open_sources.py
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import extract_places as ep

ROOT = ep.ROOT
DATA_DIR = ep.DATA_DIR
GEONAMES_ZIP = Path("/tmp/IN.zip")
GEONAMES_TXT = Path("/tmp/IN.txt")
USER_AGENT = ep.USER_AGENT

# feature class.code -> (kind phrase, category, tag)
FEATURES: dict[str, tuple[str, str, str]] = {
    "S.TMPL": ("temple", "spiritual", "temple"),
    "S.MSQE": ("mosque", "spiritual", "mosque"),
    "S.CH": ("church", "spiritual", "church"),
    "S.MSTY": ("monastery", "spiritual", "monastery"),
    "S.SHRN": ("shrine", "spiritual", "shrine"),
    "S.RLG": ("religious site", "spiritual", "pilgrimage"),
    "S.MUS": ("museum", "heritage", "museum"),
    "S.PAL": ("palace", "heritage", "palace"),
    "S.FT": ("fort", "heritage", "fort"),
    "S.HSTS": ("historical site", "heritage", "archaeological-site"),
    "S.RUIN": ("ruin", "heritage", "archaeological-site"),
    "S.ANS": ("archaeological site", "heritage", "archaeological-site"),
    "S.MNMT": ("monument", "heritage", "monument"),
    "S.TMB": ("tomb", "heritage", "monument"),
    "S.TOWR": ("tower", "heritage", "monument"),
    "S.LTHSE": ("lighthouse", "heritage", "lighthouse"),
    "S.ZOO": ("zoo", "wildlife", "zoo"),
    "S.GDN": ("garden", "nature", "garden"),
    "S.GHAT": ("ghat", "spiritual", "ghat"),
    "S.CAVE": ("cave", "nature", "cave"),
    "S.SPA": ("spring", "nature", "spring"),
    "S.MKT": ("market", "other", "market"),
    "H.FLLS": ("waterfall", "nature", "waterfall"),
    "H.LK": ("lake", "nature", "lake"),
    "H.LKI": ("seasonal lake", "nature", "lake"),
    "H.RSV": ("reservoir", "nature", "lake"),
    "H.RSVI": ("seasonal reservoir", "nature", "lake"),
    "H.SPNG": ("spring", "nature", "spring"),
    "H.BAY": ("bay", "beach", "beach"),
    "S.DAM": ("dam", "nature", "dam"),
    "T.BCH": ("beach", "beach", "beach"),
    "T.CAPE": ("cape", "beach", "beach"),
    "T.ISL": ("island", "nature", "island"),
    "T.PASS": ("mountain pass", "nature", "pass"),
    "T.PK": ("peak", "nature", "peak"),
    "T.MT": ("mountain", "nature", "mountain"),
    "T.HLL": ("hill", "nature", "hill"),
    "T.RDGE": ("ridge", "nature", "ridge"),
    "T.VAL": ("valley", "nature", "valley"),
    "T.CLF": ("cliff", "nature", "cliff"),
    "T.DUNE": ("dune", "nature", "dune"),
    "T.RK": ("rock", "nature", "rock"),
    "L.PRK": ("park", "nature", "park"),
    "L.RESN": ("nature reserve", "wildlife", "wildlife-sanctuary"),
    "L.RES": ("reserve", "wildlife", "wildlife-sanctuary"),
    "L.RESW": ("wildlife reserve", "wildlife", "wildlife-sanctuary"),
    "V.FRST": ("forest", "nature", "forest"),
}

ADMIN1 = {
    "01": "Andaman and Nicobar Islands",
    "02": "Andhra Pradesh",
    "30": "Arunachal Pradesh",
    "03": "Assam",
    "34": "Bihar",
    "37": "Chhattisgarh",
    "33": "Goa",
    "09": "Gujarat",
    "10": "Haryana",
    "11": "Himachal Pradesh",
    "38": "Jharkhand",
    "19": "Karnataka",
    "13": "Kerala",
    "35": "Madhya Pradesh",
    "16": "Maharashtra",
    "17": "Manipur",
    "18": "Meghalaya",
    "31": "Mizoram",
    "20": "Nagaland",
    "21": "Odisha",
    "23": "Punjab",
    "24": "Rajasthan",
    "29": "Sikkim",
    "25": "Tamil Nadu",
    "40": "Telangana",
    "26": "Tripura",
    "36": "Uttar Pradesh",
    "39": "Uttarakhand",
    "28": "West Bengal",
    "07": "Delhi",
    "12": "Jammu and Kashmir",
    "41": "Ladakh",
    "14": "Lakshadweep",
    "22": "Puducherry",
    "05": "Chandigarh",
    "52": "Dadra and Nagar Haveli and Daman and Diu",
}

GENERIC_NAMES = {
    "temple",
    "fort",
    "hill",
    "peak",
    "pass",
    "lake",
    "waterfall",
    "falls",
    "cave",
    "reservoir",
    "ridge",
    "valley",
    "dune",
    "dam",
    "spring",
    "island",
    "beach",
    "ghat",
    "garden",
    "park",
    "mountain",
    "shrine",
    "mosque",
    "church",
    "forest",
    "reserve",
}

OSM_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)


def ensure_geonames() -> Path:
    if GEONAMES_TXT.is_file() and GEONAMES_TXT.stat().st_size > 1_000_000:
        return GEONAMES_TXT
    print("Downloading GeoNames India dump", flush=True)
    request = urllib.request.Request(
        "https://download.geonames.org/export/dump/IN.zip",
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        GEONAMES_ZIP.write_bytes(response.read())
    with zipfile.ZipFile(GEONAMES_ZIP) as archive:
        archive.extract("IN.txt", path="/tmp")
    return GEONAMES_TXT


def load_records() -> tuple[list[dict], set[str], set[tuple[str, str]], dict[tuple[int, int], list[tuple[str, str]]]]:
    records: list[dict] = []
    used_ids: set[str] = set()
    keys: set[tuple[str, str]] = set()
    cells: dict[tuple[int, int], list[tuple[str, str]]] = {}
    for path in sorted(DATA_DIR.glob("*.json")):
        for record in json.loads(path.read_text(encoding="utf-8")):
            records.append(record)
            used_ids.add(record["id"])
            key = (ep.slug(record["name"]), record["state"])
            keys.add(key)
            coords = record.get("coordinates")
            if coords:
                cell = (round(coords["lat"] * 50), round(coords["lon"] * 50))
                cells.setdefault(cell, []).append((key[0], record["state"]))
    return records, used_ids, keys, cells


def same_place(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    return left in right or right in left


def already_mapped(
    name: str,
    state: str,
    lat: float | None,
    lon: float | None,
    keys: set[tuple[str, str]],
    cells: dict[tuple[int, int], list[tuple[str, str]]],
) -> bool:
    key = (ep.slug(name), state)
    if key[0] and key in keys:
        return True
    if lat is None or lon is None:
        return False
    cell = (round(lat * 50), round(lon * 50))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for other_slug, other_state in cells.get((cell[0] + dy, cell[1] + dx), []):
                if other_slug == key[0]:
                    return True
                if other_state == state and same_place(key[0], other_slug):
                    return True
    return False


def remember_new(
    name: str,
    state: str,
    lat: float | None,
    lon: float | None,
    keys: set[tuple[str, str]],
    cells: dict[tuple[int, int], list[tuple[str, str]]],
) -> None:
    key = (ep.slug(name), state)
    keys.add(key)
    if lat is not None and lon is not None:
        cell = (round(lat * 50), round(lon * 50))
        cells.setdefault(cell, []).append((key[0], state))


def usable_name(name: str) -> bool:
    cleaned = " ".join(name.split()).strip(" .")
    if len(cleaned) < 2 or len(cleaned) > 140:
        return False
    if ep.slug(cleaned) in GENERIC_NAMES:
        return False
    if "unnamed" in cleaned.lower() or "<br" in cleaned.lower():
        return False
    if not ep.is_tourism_record(cleaned, cleaned):
        return False
    return True


def build_record(
    name: str,
    state: str,
    kind: str,
    category: str,
    tag: str,
    lat: float | None,
    lon: float | None,
    elevation: int | None,
    used_ids: set[str],
    source: str,
) -> dict:
    description = f"{name} is a {kind} in {state}, India."
    facts = [f"Listed in {source} as a {kind} in {state}."]
    if elevation is not None and elevation > 0 and kind in {
        "mountain",
        "peak",
        "hill",
        "mountain pass",
        "waterfall",
        "cave",
        "ridge",
        "cliff",
        "dune",
        "temple",
        "fort",
        "shrine",
    }:
        facts.append(f"Mapped elevation is about {elevation:,} m.")
    facts.append("Included because mapped sites often stay off visitor itineraries.")
    facts = facts[:6]
    record = {
        "id": ep.unique_id(name, state, None, used_ids),
        "name": name,
        "state": state,
        "category": category,
        "description": description,
        "facts": facts,
        "tags": ["lesser-known", "mapped", tag],
    }
    if lat is not None and lon is not None and ep.in_india(lat, lon):
        record["coordinates"] = {"lat": round(lat, 5), "lon": round(lon, 5)}
    if category == "hill-station":
        record["category"] = "hill-station"
    return record


def build_place_index(path: Path) -> dict[tuple[int, int], list[tuple[float, float, str]]]:
    """Nearest-town index so enclave union territories do not claim whole states."""
    grid: dict[tuple[int, int], list[tuple[float, float, str]]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            parts = line.split("\t")
            if len(parts) < 11 or parts[6] != "P" or not parts[7].startswith("PPL"):
                continue
            state = ADMIN1.get(parts[10])
            if not state:
                continue
            try:
                lat = float(parts[4])
                lon = float(parts[5])
            except ValueError:
                continue
            grid.setdefault((int(lat * 2), int(lon * 2)), []).append((lat, lon, state))
    return grid


# Tight extents for union territories whose GeoNames admin codes are sometimes
# applied far outside the territory.
SMALL_UT_BOXES: dict[str, list[tuple[float, float, float, float]]] = {
    "Chandigarh": [(30.66, 30.80, 76.70, 76.85)],
    "Delhi": [(28.40, 28.88, 76.84, 77.35)],
    "Puducherry": [
        (11.87, 11.98, 79.74, 79.86),
        (10.85, 11.05, 79.75, 79.90),
        (11.68, 11.76, 75.50, 75.58),
        (16.70, 16.76, 82.15, 82.28),
    ],
    "Lakshadweep": [(8.0, 12.4, 71.6, 74.1)],
    "Dadra and Nagar Haveli and Daman and Diu": [
        (20.00, 20.50, 72.75, 73.20),
        (20.65, 20.76, 70.90, 71.05),
    ],
    "Andaman and Nicobar Islands": [(6.5, 13.8, 92.0, 94.3)],
}


def inside_territory(lat: float, lon: float, state: str) -> bool:
    boxes = SMALL_UT_BOXES.get(state)
    if not boxes:
        return True
    return any(south <= lat <= north and west <= lon <= east for south, north, west, east in boxes)


def nearest_towns(
    lat: float,
    lon: float,
    grid: dict[tuple[int, int], list[tuple[float, float, str]]],
) -> list[tuple[float, str]]:
    base = (int(lat * 2), int(lon * 2))
    found: list[tuple[float, str]] = []
    for radius in (1, 3, 6):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                for plat, plon, state in grid.get((base[0] + dy, base[1] + dx), []):
                    found.append(((plat - lat) ** 2 + (plon - lon) ** 2, state))
        if found:
            break
    found.sort()
    return found


def state_for_point(
    lat: float,
    lon: float,
    grid: dict[tuple[int, int], list[tuple[float, float, str]]],
) -> str | None:
    for _distance, state in nearest_towns(lat, lon, grid):
        if inside_territory(lat, lon, state):
            return state
    return None


def prefer_admin_state(
    lat: float,
    lon: float,
    coded: str | None,
    grid: dict[tuple[int, int], list[tuple[float, float, str]]],
) -> str | None:
    if coded and not inside_territory(lat, lon, coded):
        return state_for_point(lat, lon, grid)
    nearest = state_for_point(lat, lon, grid)
    if not coded:
        return nearest
    if not nearest or nearest == coded:
        return coded
    same = [distance for distance, state in nearest_towns(lat, lon, grid) if state == coded]
    other = [distance for distance, state in nearest_towns(lat, lon, grid) if state == nearest]
    if same and other and same[0] > other[0] + 0.04:
        return nearest
    return coded


def add_geonames(
    path: Path,
    records: list[dict],
    used_ids: set[str],
    keys: set[tuple[str, str]],
    cells: dict[tuple[int, int], list[tuple[str, str]]],
    grid: dict[tuple[int, int], list[tuple[float, float, str]]],
) -> int:
    added = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 17:
                continue
            code = f"{parts[6]}.{parts[7]}"
            spec = FEATURES.get(code)
            if not spec:
                continue
            kind, category, tag = spec
            name = parts[1].strip() or parts[2].strip()
            if not usable_name(name):
                continue
            try:
                lat = float(parts[4])
                lon = float(parts[5])
            except ValueError:
                continue
            if not ep.in_india(lat, lon):
                continue
            state = prefer_admin_state(lat, lon, ADMIN1.get(parts[10]), grid)
            if not state:
                continue
            if "sanctuary" in name.lower() or "national park" in name.lower() or "tiger" in name.lower():
                category = "wildlife"
            if "hill station" in name.lower():
                category = "hill-station"
            if already_mapped(name, state, lat, lon, keys, cells):
                continue
            try:
                elevation = int(float(parts[16]))
            except ValueError:
                elevation = None
            if elevation is not None and (elevation <= 0 or elevation > 8849):
                elevation = None
            record = build_record(
                name, state, kind, category, tag, lat, lon, elevation, used_ids, "geographic records"
            )
            records.append(record)
            remember_new(name, state, lat, lon, keys, cells)
            added += 1
    print(f"GeoNames added {added}", flush=True)
    return added


def overpass(query: str) -> list[dict] | None:
    payload = urllib.parse.urlencode({"data": query}).encode()
    for endpoint in OSM_ENDPOINTS:
        request = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"User-Agent": USER_AGENT},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.load(response)
            return data.get("elements", [])
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"  overpass failed: {exc}", flush=True)
    return None


def osm_tiles() -> list[tuple[float, float, float, float]]:
    tiles = []
    lat = 6.0
    while lat < 37:
        lon = 68.0
        while lon < 98:
            tiles.append((lat, lon, min(lat + 5, 37), min(lon + 6, 98)))
            lon += 6
        lat += 5
    return tiles


def element_point(element: dict) -> tuple[float, float] | None:
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    center = element.get("center") or {}
    if "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])
    return None


def osm_kind(tags: dict) -> tuple[str, str, str] | None:
    tourism = tags.get("tourism") or ""
    historic = tags.get("historic") or ""
    natural = tags.get("natural") or ""
    mapping = {
        "viewpoint": ("viewpoint", "nature", "viewpoint"),
        "attraction": ("attraction", "other", "attraction"),
        "museum": ("museum", "heritage", "museum"),
        "zoo": ("zoo", "wildlife", "zoo"),
        "theme_park": ("theme park", "other", "theme-park"),
        "fort": ("fort", "heritage", "fort"),
        "ruins": ("ruin", "heritage", "archaeological-site"),
        "archaeological_site": ("archaeological site", "heritage", "archaeological-site"),
        "monument": ("monument", "heritage", "monument"),
        "tomb": ("tomb", "heritage", "monument"),
        "palace": ("palace", "heritage", "palace"),
        "monastery": ("monastery", "spiritual", "monastery"),
        "temple": ("temple", "spiritual", "temple"),
        "waterfall": ("waterfall", "nature", "waterfall"),
        "cave_entrance": ("cave", "nature", "cave"),
        "beach": ("beach", "beach", "beach"),
        "peak": ("peak", "nature", "peak"),
        "hot_spring": ("hot spring", "nature", "spring"),
    }
    for key in (tourism, historic, natural):
        if key in mapping:
            return mapping[key]
    return None


def add_openstreetmap(
    records: list[dict],
    used_ids: set[str],
    keys: set[tuple[str, str]],
    cells: dict[tuple[int, int], list[tuple[str, str]]],
    grid: dict[tuple[int, int], list[tuple[float, float, str]]],
) -> int:
    added = 0
    tiles = osm_tiles()
    for index, (south, west, north, east) in enumerate(tiles, start=1):
        query = f"""
[out:json][timeout:50];
(
  nwr["name"]["tourism"~"^(viewpoint|attraction|museum|zoo|theme_park)$"]({south},{west},{north},{east});
  nwr["name"]["historic"~"^(archaeological_site|ruins)$"]({south},{west},{north},{east});
  nwr["name"]["natural"~"^(waterfall|cave_entrance|beach|hot_spring)$"]({south},{west},{north},{east});
);
out tags center;
"""
        print(f"OSM tile {index}/{len(tiles)} {south:.0f},{west:.0f}", flush=True)
        elements = overpass(query)
        if elements is None:
            print("OpenStreetMap left unfinished after a timeout; mapped places already saved stay.", flush=True)
            return added
        for element in elements:
            tags = element.get("tags") or {}
            spec = osm_kind(tags)
            name = (tags.get("name:en") or tags.get("name") or "").strip()
            point = element_point(element)
            if not spec or not point or not usable_name(name):
                continue
            kind, category, tag = spec
            lat, lon = point
            if not ep.in_india(lat, lon):
                continue
            state = state_for_point(lat, lon, grid)
            if not state:
                continue
            if already_mapped(name, state, lat, lon, keys, cells):
                continue
            elevation = None
            if tags.get("ele"):
                try:
                    elevation = int(float(tags["ele"].split(";")[0]))
                except ValueError:
                    elevation = None
            record = build_record(
                name, state, kind, category, tag, lat, lon, elevation, used_ids, "map data"
            )
            records.append(record)
            remember_new(name, state, lat, lon, keys, cells)
            added += 1
        time.sleep(1)
    print(f"OpenStreetMap added {added}", flush=True)
    return added


def write_records(records: list[dict]) -> None:
    grouped: dict[str, list[dict]] = {}
    for record in records:
        grouped.setdefault(record["state"], []).append(record)
    for state in ep.STATES:
        state_records = sorted(grouped.get(state, []), key=lambda item: item["id"])
        if not state_records:
            print(f"WARNING: no places for {state}", flush=True)
            continue
        path = DATA_DIR / f"{ep.slug(state)}.json"
        path.write_text(
            json.dumps(state_records, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"{state}: {len(state_records)}", flush=True)
    print(f"Wrote {len(records)} places", flush=True)


WD_TYPES = (
    ("Q842402", "temple", "spiritual", "temple"),
    ("Q32815", "mosque", "spiritual", "mosque"),
    ("Q16970", "church", "spiritual", "church"),
    ("Q44613", "monastery", "spiritual", "monastery"),
    ("Q1785071", "fort", "heritage", "fort"),
    ("Q16560", "palace", "heritage", "palace"),
    ("Q34038", "waterfall", "nature", "waterfall"),
    ("Q35509", "cave", "nature", "cave"),
    ("Q40080", "beach", "beach", "beach"),
    ("Q23397", "lake", "nature", "lake"),
    ("Q46169", "national park", "wildlife", "national-park"),
    ("Q33506", "museum", "heritage", "museum"),
    ("Q4989906", "monument", "heritage", "monument"),
    ("Q839954", "archaeological site", "heritage", "archaeological-site"),
)


def add_wikidata(
    records: list[dict],
    used_ids: set[str],
    keys: set[tuple[str, str]],
    cells: dict[tuple[int, int], list[tuple[str, str]]],
    grid: dict[tuple[int, int], list[tuple[float, float, str]]],
) -> int:
    added = 0
    for qid, kind, category, tag in WD_TYPES:
        query = f"""
SELECT ?itemLabel ?lat ?lon WHERE {{
  ?item wdt:P31 wd:{qid} ; wdt:P17 wd:Q668 ; p:P625/psv:P625 ?coord .
  ?coord wikibase:geoLatitude ?lat ; wikibase:geoLongitude ?lon .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
"""
        url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": query})
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
        )
        print(f"Wikidata {kind}", flush=True)
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"  skipped {kind}: {exc}", flush=True)
            continue
        for row in data.get("results", {}).get("bindings", []):
            name = row.get("itemLabel", {}).get("value", "").strip()
            if not name or name.startswith("Q") and name[1:].isdigit():
                continue
            try:
                lat = float(row["lat"]["value"])
                lon = float(row["lon"]["value"])
            except (KeyError, ValueError):
                continue
            if not usable_name(name) or not ep.in_india(lat, lon):
                continue
            state = state_for_point(lat, lon, grid)
            if not state or already_mapped(name, state, lat, lon, keys, cells):
                continue
            row_category = "hill-station" if "hill station" in name.lower() else category
            record = build_record(
                name, state, kind, row_category, tag, lat, lon, None, used_ids, "structured geographic data"
            )
            records.append(record)
            remember_new(name, state, lat, lon, keys, cells)
            added += 1
        time.sleep(1)
    print(f"Wikidata added {added}", flush=True)
    return added


def main() -> int:
    path = ensure_geonames()
    grid = build_place_index(path)
    records, used_ids, keys, cells = load_records()
    kept = [
        record
        for record in records
        if "mapped" not in (record.get("tags") or [])
        and ep.is_tourism_record(record["name"], record.get("description") or record["name"])
    ]
    if len(kept) != len(records):
        print(f"Removed {len(records) - len(kept)} previously mapped rows before reload", flush=True)
        records = kept
        used_ids = {record["id"] for record in records}
        keys = {(ep.slug(record["name"]), record["state"]) for record in records}
        cells = {}
        for record in records:
            coords = record.get("coordinates")
            if not coords:
                continue
            cell = (round(coords["lat"] * 50), round(coords["lon"] * 50))
            cells.setdefault(cell, []).append((ep.slug(record["name"]), record["state"]))
    before = len(records)
    add_geonames(path, records, used_ids, keys, cells, grid)
    write_records(records)
    add_wikidata(records, used_ids, keys, cells, grid)
    write_records(records)
    add_openstreetmap(records, used_ids, keys, cells, grid)
    write_records(records)
    print(f"Added {len(records) - before} places", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
