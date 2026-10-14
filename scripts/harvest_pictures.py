#!/usr/bin/env python3
"""Store openly licensed image references for catalog places.

Image URLs come from the Wikimedia Commons API. Files without a free
license in the API metadata are skipped. Place states and districts are
not changed, and no image files are downloaded.
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import extract_places as ep

ROOT = ep.ROOT
PLACES_DIR = ep.DATA_DIR
OVERLAY_DIR = ROOT / "data" / "enrichment-overlay"
PICTURE_DIR = ROOT / "data" / "picture-overlay"
SEARCHED_PATH = PICTURE_DIR / "searched-ids.json"
COVERAGE_PATH = ROOT / "data" / "coverage-summary.json"
GAPS_PATH = ROOT / "data" / "gaps.json"
USER_AGENT = ep.USER_AGENT
COMMONS = "https://commons.wikimedia.org/w/api.php"

STOP = {
    "falls",
    "fall",
    "temple",
    "lake",
    "park",
    "fort",
    "hill",
    "hills",
    "peak",
    "cave",
    "beach",
    "river",
    "wildlife",
    "sanctuary",
    "national",
    "india",
    "state",
    "the",
    "and",
    "with",
}
FOREIGN_RE = re.compile(
    r"esopus|newfoundland|canada|australia|england|london|africa|europe|united states|"
    r"new york|california|scotland|ireland|wales|france|germany|italy|spain|china|japan|"
    r"nepal|bhutan|bangladesh|pakistan|sri lanka|thailand|myanmar",
    re.I,
)
STATE_ALIASES = {
    "Andaman and Nicobar Islands": ["andaman", "nicobar"],
    "Andhra Pradesh": ["andhra"],
    "Arunachal Pradesh": ["arunachal"],
    "Assam": ["assam"],
    "Bihar": ["bihar"],
    "Chandigarh": ["chandigarh"],
    "Chhattisgarh": ["chhattisgarh", "chattisgarh"],
    "Dadra and Nagar Haveli and Daman and Diu": ["dadra", "daman", "diu", "silvassa"],
    "Delhi": ["delhi"],
    "Goa": ["goa"],
    "Gujarat": ["gujarat"],
    "Haryana": ["haryana"],
    "Himachal Pradesh": ["himachal", "shimla"],
    "Jammu and Kashmir": ["kashmir", "jammu"],
    "Jharkhand": ["jharkhand"],
    "Karnataka": ["karnataka"],
    "Kerala": ["kerala"],
    "Ladakh": ["ladakh"],
    "Lakshadweep": ["lakshadweep"],
    "Madhya Pradesh": ["madhya pradesh"],
    "Maharashtra": ["maharashtra"],
    "Manipur": ["manipur"],
    "Meghalaya": ["meghalaya", "khasi", "garo", "jaintia", "shillong"],
    "Mizoram": ["mizoram", "aizawl"],
    "Nagaland": ["nagaland", "kohima"],
    "Odisha": ["odisha", "orissa"],
    "Puducherry": ["puducherry", "pondicherry"],
    "Punjab": ["punjab"],
    "Rajasthan": ["rajasthan"],
    "Sikkim": ["sikkim"],
    "Tamil Nadu": ["tamil"],
    "Telangana": ["telangana"],
    "Tripura": ["tripura", "agartala"],
    "Uttar Pradesh": ["uttar pradesh"],
    "Uttarakhand": ["uttarakhand", "uttaranchal"],
    "West Bengal": ["west bengal", "bengal", "kolkata"],
}
AMBIGUOUS = {
    "bishop",
    "elephant",
    "sweet",
    "blue",
    "heaven",
    "living",
    "double",
    "root",
    "bridge",
    "buddhist",
    "church",
    "palace",
    "museum",
    "garden",
    "memorial",
    "ancient",
    "stone",
    "waterfall",
    "springs",
    "valley",
    "island",
    "point",
    "rock",
}


def file_is_local(name: str, state: str, filename: str) -> bool:
    folded = filename.lower().replace("_", " ")
    if FOREIGN_RE.search(folded):
        return False
    if not title_matches(name, filename):
        return False
    aliases = STATE_ALIASES.get(state, [state.lower()])
    if any(alias in folded for alias in aliases) or "india" in folded:
        return True
    distinctive = [token for token in tokens(name) if len(token) >= 6 and token not in AMBIGUOUS]
    return any(token in folded for token in distinctive)


FREE_RE = re.compile(
    r"public domain|\bcc0\b|\bcc[- ]by\b|\bcc[- ]by[- ]sa\b|gfdl|gnu free documentation",
    re.I,
)
CLOSED_RE = re.compile(
    r"non-?commercial|no derivatives|all rights reserved|fair use|copyrighted|\bcc[- ]by[- ]nc\b|\bcc[- ]by[- ]nd\b",
    re.I,
)


def api_get(params: dict[str, str]) -> dict:
    url = COMMONS + "?" + urllib.parse.urlencode({**params, "format": "json"})
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.load(response)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def tokens(name: str) -> list[str]:
    words = [word.lower() for word in re.findall(r"[A-Za-z]{4,}", name)]
    kept = [word for word in words if word not in STOP]
    if kept:
        return kept
    return [word.lower() for word in re.findall(r"[A-Za-z]{4,}", name)][:2]


def title_matches(name: str, filename: str) -> bool:
    folded = filename.lower().replace("_", " ")
    needed = tokens(name)
    if not needed:
        return False
    return any(token in folded for token in needed)


def search_files(name: str, state: str) -> list[str]:
    found: list[str] = []
    for query in (f'"{name}" {state}', f"{name} {state}"):
        try:
            data = api_get(
                {
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srnamespace": "6",
                    "srlimit": "8",
                }
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  search failed for {name}: {exc}", flush=True)
            return found
        for row in (data.get("query") or {}).get("search") or []:
            title = row.get("title") or ""
            if title.startswith("File:") and file_is_local(name, state, title) and title not in found:
                found.append(title)
        if found:
            return found[:5]
        time.sleep(0.05)
    return found


def license_name(info: dict) -> str:
    meta = info.get("extmetadata") or {}
    short = ((meta.get("LicenseShortName") or {}).get("value") or "").strip()
    if short:
        return re.sub(r"<[^>]+>", "", short)
    return ((meta.get("License") or {}).get("value") or "").strip()


def image_details(titles: list[str]) -> list[dict]:
    if not titles:
        return []
    try:
        data = api_get(
            {
                "action": "query",
                "titles": "|".join(titles),
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|mime",
            }
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  imageinfo failed: {exc}", flush=True)
        return []
    pages = (data.get("query") or {}).get("pages") or {}
    rows = []
    for page in pages.values():
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        license_text = license_name(info)
        if not license_text or CLOSED_RE.search(license_text) or not FREE_RE.search(license_text):
            continue
        url = info.get("url") or ""
        if not url.startswith("https://upload.wikimedia.org/"):
            continue
        filename = (page.get("title") or "").removeprefix("File:")
        rows.append(
            {
                "image_url": url,
                "title": page.get("title") or filename,
                "caption": filename.replace("_", " "),
                "source_url": "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(filename),
                "license_note": license_text,
            }
        )
    return rows


def cite_photo(item: dict, image: dict) -> None:
    facts = item.setdefault("visitor_facts", [])
    text = f"Wikimedia Commons has an openly licensed file for this place: {image['caption']}."
    if len(text) > 240 or any(fact.get("text") == text for fact in facts):
        return
    facts.append(
        {
            "theme": "photo",
            "text": text,
            "basis": "cited-source",
            "source": image["source_url"],
        }
    )
    sources = item.setdefault("sources", [])
    if not any(source.get("url") == image["source_url"] for source in sources):
        sources.append({"url": image["source_url"], "publisher": "commons.wikimedia.org"})
    item["collection_status"] = "enriched"


def picture_record(place: dict, images: list[dict]) -> dict:
    return {
        "id": place["id"],
        "name": place["name"],
        "state": place["state"],
        "images": images[:5],
    }


def refresh_reports() -> None:
    coverage = load_json(COVERAGE_PATH)
    gaps = load_json(GAPS_PATH)
    by_state = {row["state"]: row for row in coverage["states"]}
    with_images = 0
    total = 0
    for path in sorted(PLACES_DIR.glob("*.json")):
        places = load_json(path)
        total += len(places)
        state = places[0]["state"] if places else ""
        picture_path = PICTURE_DIR / path.name
        images = 0
        if picture_path.is_file():
            images = sum(1 for item in load_json(picture_path) if item.get("images"))
        with_images += images
        if state in by_state:
            by_state[state]["with_picture_references"] = images
            by_state[state]["picture_reference_percent"] = round(100 * images / len(places), 1) if places else 0
    coverage["with_picture_references"] = with_images
    coverage["picture_reference_percent"] = round(100 * with_images / total, 1) if total else 0
    dump_json(COVERAGE_PATH, coverage)
    gaps["with_picture_references"] = with_images
    gaps["missing_picture_references"] = total - with_images
    gaps["picture_note"] = (
        "Picture references are Wikimedia Commons files whose API metadata names a free license. "
        "Places without such a file are left without an image entry."
    )
    dump_json(GAPS_PATH, gaps)


def harvest_state(state_file: Path, searched: set[str], limit: int) -> int:
    places = load_json(PLACES_DIR / state_file.name)
    overlay = {item["id"]: item for item in load_json(OVERLAY_DIR / state_file.name)}
    picture_path = PICTURE_DIR / state_file.name
    existing = []
    if picture_path.is_file():
        existing = load_json(picture_path)
    by_id = {item["id"]: item for item in existing}
    added = 0
    checked = 0
    for place in places:
        if limit <= 0:
            break
        if place["id"] in searched or place["id"] in by_id:
            continue
        checked += 1
        limit -= 1
        searched.add(place["id"])
        titles = search_files(place["name"], place["state"])
        images = image_details(titles)
        time.sleep(0.12)
        if not images:
            if checked % 25 == 0:
                print(f"  {place['state']}: checked {checked}, new image sets {added}", flush=True)
            continue
        by_id[place["id"]] = picture_record(place, images)
        item = overlay.get(place["id"])
        if item is not None:
            cite_photo(item, images[0])
        added += 1
        if checked % 25 == 0:
            print(f"  {place['state']}: checked {checked}, new image sets {added}", flush=True)
    if by_id:
        dump_json(picture_path, sorted(by_id.values(), key=lambda item: item["id"]))
    dump_json(OVERLAY_DIR / state_file.name, sorted(overlay.values(), key=lambda item: item["id"]))
    print(f"{places[0]['state'] if places else state_file.name}: added {added} picture sets", flush=True)
    return limit


def main() -> int:
    import sys

    cap = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    PICTURE_DIR.mkdir(parents=True, exist_ok=True)
    searched = set(load_json(SEARCHED_PATH)) if SEARCHED_PATH.is_file() else set()
    # Thin files and visitor-heavy coasts first, then the rest.
    preferred = [
        "meghalaya.json",
        "nagaland.json",
        "tripura.json",
        "mizoram.json",
        "arunachal-pradesh.json",
        "manipur.json",
        "sikkim.json",
        "andaman-and-nicobar-islands.json",
        "goa.json",
        "puducherry.json",
        "lakshadweep.json",
        "chandigarh.json",
    ]
    files = [PLACES_DIR / name for name in preferred if (PLACES_DIR / name).is_file()]
    files.extend(path for path in sorted(PLACES_DIR.glob("*.json")) if path not in files)
    remaining = cap
    for path in files:
        if remaining <= 0:
            break
        before = remaining
        remaining = harvest_state(path, searched, remaining)
        dump_json(SEARCHED_PATH, sorted(searched))
        refresh_reports()
        print(f"Batch status: used {before - remaining} lookups, {cap - remaining} of {cap}", flush=True)
    print(f"Lookups this run: {cap - remaining}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
