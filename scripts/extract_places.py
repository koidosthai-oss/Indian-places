#!/usr/bin/env python3
"""Extract Indian tourism places from Wikipedia categories and Wikidata.

Discovery uses the English Wikipedia category graph and the places linked
from tourism list pages (attractions, forts, temples, parks, beaches,
wildlife, monuments, and lesser-known collections in every state and union
territory). Names, coordinates, descriptions, and short facts come from
Wikidata claims, which are CC0. Wikipedia article prose is not copied.

Regenerate the catalog with:

    .venv/bin/python scripts/extract_places.py
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "places"
SAMPLE_PATH = DATA_DIR / "sample.json"
CRAWL_CACHE = Path("/tmp/indian-places-pages.json")

USER_AGENT = (
    "IndianPlacesBot/1.0 "
    "(https://github.com/koidosthai-oss/Indian-places; tourism dataset)"
)

# Current states and union territories. Longer names must be matched first.
STATES: list[str] = [
    "Dadra and Nagar Haveli and Daman and Diu",
    "Andaman and Nicobar Islands",
    "Jammu and Kashmir",
    "Arunachal Pradesh",
    "Himachal Pradesh",
    "Madhya Pradesh",
    "Uttar Pradesh",
    "Andhra Pradesh",
    "West Bengal",
    "Tamil Nadu",
    "Chhattisgarh",
    "Uttarakhand",
    "Maharashtra",
    "Lakshadweep",
    "Chandigarh",
    "Puducherry",
    "Jharkhand",
    "Karnataka",
    "Rajasthan",
    "Telangana",
    "Meghalaya",
    "Nagaland",
    "Haryana",
    "Gujarat",
    "Manipur",
    "Mizoram",
    "Tripura",
    "Kerala",
    "Odisha",
    "Punjab",
    "Sikkim",
    "Assam",
    "Bihar",
    "Delhi",
    "Ladakh",
    "Goa",
]

STATE_ALIASES = {
    "Orissa": "Odisha",
    "Pondicherry": "Puducherry",
    "NCT of Delhi": "Delhi",
    "National Capital Territory of Delhi": "Delhi",
}

# Administrative items that are the state or union territory itself.
STATE_QIDS = {
    "Q1159": "Andhra Pradesh",
    "Q1162": "Arunachal Pradesh",
    "Q1164": "Assam",
    "Q1165": "Bihar",
    "Q1168": "Chhattisgarh",
    "Q1171": "Goa",
    "Q1061": "Gujarat",
    "Q1174": "Haryana",
    "Q1177": "Himachal Pradesh",
    "Q1184": "Jharkhand",
    "Q1185": "Karnataka",
    "Q1186": "Kerala",
    "Q1188": "Madhya Pradesh",
    "Q1191": "Maharashtra",
    "Q1193": "Manipur",
    "Q1195": "Meghalaya",
    "Q1502": "Mizoram",
    "Q1599": "Nagaland",
    "Q22048": "Odisha",
    "Q22424": "Punjab",
    "Q1437": "Rajasthan",
    "Q1505": "Sikkim",
    "Q1445": "Tamil Nadu",
    "Q677037": "Telangana",
    "Q1363": "Tripura",
    "Q1498": "Uttar Pradesh",
    "Q1499": "Uttarakhand",
    "Q1356": "West Bengal",
    "Q40888": "Andaman and Nicobar Islands",
    "Q43433": "Chandigarh",
    "Q77997266": "Dadra and Nagar Haveli and Daman and Diu",
    "Q9357528": "Delhi",
    "Q1353": "Delhi",
    "Q1180": "Jammu and Kashmir",
    "Q200667": "Ladakh",
    "Q26927": "Lakshadweep",
    "Q66743": "Puducherry",
}

ISO_REGION = {
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CG": "Chhattisgarh",
    "CT": "Chhattisgarh",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HR": "Haryana",
    "HP": "Himachal Pradesh",
    "JH": "Jharkhand",
    "KA": "Karnataka",
    "KL": "Kerala",
    "MP": "Madhya Pradesh",
    "MH": "Maharashtra",
    "MN": "Manipur",
    "ML": "Meghalaya",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "OD": "Odisha",
    "OR": "Odisha",
    "PB": "Punjab",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TN": "Tamil Nadu",
    "TG": "Telangana",
    "TS": "Telangana",
    "TR": "Tripura",
    "UP": "Uttar Pradesh",
    "UK": "Uttarakhand",
    "UT": "Uttarakhand",
    "WB": "West Bengal",
    "AN": "Andaman and Nicobar Islands",
    "CH": "Chandigarh",
    "DH": "Dadra and Nagar Haveli and Daman and Diu",
    "DD": "Dadra and Nagar Haveli and Daman and Diu",
    "DN": "Dadra and Nagar Haveli and Daman and Diu",
    "DL": "Delhi",
    "JK": "Jammu and Kashmir",
    "LA": "Ladakh",
    "LD": "Lakshadweep",
    "PY": "Puducherry",
}

SEEDS = [
    "Category:Tourist attractions in India by state or union territory",
    "Category:Archaeological sites in India by state or union territory",
    "Category:Beaches of India by state or union territory",
    "Category:Caves of India by state or union territory",
    "Category:Forts in India by state or union territory",
    "Category:Hill stations in India by state or union territory",
    "Category:Lakes of India by state or union territory",
    "Category:Monuments and memorials in India by state or union territory",
    "Category:Museums in India by state or union territory",
    "Category:Palaces in India by state or union territory",
    "Category:Protected areas of India by state or union territory",
    "Category:Wildlife sanctuaries of India by state or union territory",
    "Category:Waterfalls of India by state or union territory",
    "Category:National parks of India by state or union territory",
    "Category:World Heritage Sites in India",
    "Category:Tiger reserves of India",
    "Category:Bird sanctuaries of India",
    "Category:Biosphere reserves of India",
    "Category:Elephant reserves of India",
    "Category:Hindu temples in India by state or union territory",
    "Category:Mosques in India by state or union territory",
    "Category:Gurdwaras in India",
    "Category:Churches in India",
    "Category:Jain temples in India",
    "Category:Buddhist temples in India by state or union territory",
    "Category:Buddhist monasteries in India by state or union territory",
    "Category:Hindu pilgrimage sites in India",
    "Category:Buddhist pilgrimage sites in India",
    "Category:Dargahs in India",
    "Category:Stupas in India",
    "Category:Islands of Lakshadweep",
    "Category:Tourist attractions in Chandigarh",
    "Category:Lists of tourist attractions in India",
    "Category:Lists of tourist attractions in India by state or union territory",
    "Category:Tourism in India by state or union territory",
    "Category:Stepwells in India",
    "Category:Hot springs of India",
    "Category:Hill stations in India",
]

LIST_CATEGORY_KEEP = re.compile(
    r"tourist|attraction|fort|temple|beach|waterfall|lake|cave|palace|museum|"
    r"monument|park|sanctuary|heritage|hill station|pilgrimage|mosque|church|"
    r"monastery|gurdwara|gurudwara|island|wildlife|dam|garden|zoo|lighthouse|"
    r"stepwell|hot spring|protected|statue|rock|clock tower|science centre|"
    r"botanical|aquarium|aquaria|valley|national importance|state protected|"
    r"palace|memorial|waterfall|trek",
    re.I,
)

SKIP_RE = re.compile(
    r"(festivals?\b|defunct|\bpeople\b|births\b|deaths\b|"
    r"establishments?\b|\d+(?:st|nd|rd|th)-century|wikipedia|templates?\b|"
    r"\bimages?\b|photographs?|\bfilms?\b|\balbums?\b|\bsongs?\b|cuisine|"
    r"railway stations|airports?\b|schools?\b|hospitals?\b|companies|"
    r"newspapers|alumni|politicians|\bplayers\b|biography|userboxes|"
    r"wikiproject|navigational|disambiguation)",
    re.I,
)

NON_PLACE_RE = re.compile(
    r"(human|film|television|album|song|literary work|disambiguation|"
    r"wikimedia list|wikimedia category|newspaper|business|company|"
    r"political party|election|cricket|footballer|writer|politician|"
    r"academic journal|railway station|airport|school|hospital|"
    r"broadcaster|dance|music genre|festival|census|dialect|language|"
    r"decoration|software|agency|corporation|magazine|airline|bank|"
    r"organisation|organization|website|brand|genre)",
    re.I,
)
PLACE_RE = re.compile(
    r"(temple|fort|palace|park|beach|lake|museum|monument|waterfall|cave|"
    r"sanctuary|church|mosque|monastery|gurdwara|garden|zoo|island|hill|"
    r"valley|river|dam|reservoir|ghat|tomb|memorial|shrine|basilica|"
    r"cathedral|stepwell|spring|peak|mountain|forest|wildlife|attraction|"
    r"village|city|town|waterfall|falls|national park)",
    re.I,
)

TAG_RULES: list[tuple[str, list[str]]] = [
    ("world-heritage", ["world heritage", "unesco"]),
    ("national-park", ["national park"]),
    ("wildlife-sanctuary", ["wildlife sanctuary"]),
    ("tiger-reserve", ["tiger reserve"]),
    ("hill-station", ["hill station"]),
    ("beach", ["beach"]),
    ("fort", ["fort"]),
    ("palace", ["palace"]),
    ("temple", ["temple"]),
    ("mosque", ["mosque"]),
    ("monastery", ["monastery"]),
    ("church", ["church"]),
    ("waterfall", ["waterfall", "falls"]),
    ("cave", ["cave"]),
    ("lake", ["lake"]),
    ("museum", ["museum"]),
    ("island", ["island"]),
    ("archaeological-site", ["archaeological"]),
    ("pilgrimage", ["pilgrimage", "dargah"]),
]

# Kept when the crawl does not already include these starter records.
SEED_RECORDS = [
    {
        "id": "chitkul-himachal",
        "name": "Chitkul",
        "state": "Himachal Pradesh",
        "category": "offbeat",
        "description": (
            "Last inhabited village near the Indo-Tibet border on the Baspa "
            "River, known for wooden houses and mountain views."
        ),
        "coordinates": {"lat": 31.3504, "lon": 78.4812},
        "tags": ["hidden-gem", "village", "baspa-valley", "lesser-known"],
        "facts": [
            "It is the last inhabited village on the Baspa River before the Indo-Tibet border.",
            "Wooden houses and open mountain views are the draw in the valley.",
        ],
    },
    {
        "id": "chettinad-tamil-nadu",
        "name": "Chettinad",
        "state": "Tamil Nadu",
        "category": "heritage",
        "description": (
            "Region of ornate mansions, tile work, and distinctive cuisine "
            "in the Sivaganga district."
        ),
        "coordinates": {"lat": 10.1632, "lon": 78.8103},
        "tags": ["architecture", "food", "lesser-known"],
        "facts": [
            "The mansions are known for Athangudi tiles and imported teak.",
            "Chettinad cuisine is a distinct part of the region's identity.",
        ],
    },
]


def slug(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def state_from_text(text: str) -> str | None:
    for alias, canonical in sorted(STATE_ALIASES.items(), key=lambda item: -len(item[0])):
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return canonical
    for name in STATES:
        if re.search(rf"\b{re.escape(name)}\b", text):
            return name
    return None


def cat_name(title: str) -> str:
    return title.removeprefix("Category:")


def should_skip_category(title: str) -> bool:
    name = cat_name(title)
    if re.search(r"\b(hotels?|airports?|airlines?|highways?|corporations?)\b", name, re.I):
        return True
    if re.search(r"\blists? of\b", name, re.I):
        if re.search(r"festival", name, re.I):
            return True
        return LIST_CATEGORY_KEEP.search(name) is None
    return bool(SKIP_RE.search(name))


def is_list_title(title: str) -> bool:
    return title.startswith(("List ", "Lists ", "Index ", "Outline "))


def mentions_india(title: str) -> bool:
    if re.search(r"Indian Ocean|British Indian Ocean|West Indies|East Indies", title):
        return False
    if re.search(r"\bIndia\b", title):
        return True
    if re.search(r"\bIndian\b", title):
        return True
    return state_from_text(title) is not None


def inherited_list_state(title: str, inherited: str | None) -> str | None:
    """National lists must not stamp every linked place with a parent state."""
    named = state_from_text(title)
    if named:
        return named
    if re.search(r"\bIndia\b", title):
        return None
    return inherited


def should_expand_list(title: str) -> bool:
    if not is_list_title(title):
        return False
    if not mentions_india(title):
        return False
    if re.search(
        r"festival|chief minister|governor|election|film|song|book|highway|"
        r"airport|hotel|college|university|school|bird( species)? in",
        title,
        re.I,
    ):
        return False
    return LIST_CATEGORY_KEEP.search(title) is not None or "tourist" in title.lower()


def boring_link(title: str) -> bool:
    if title in STATES or title in {"India", "Indian people"}:
        return True
    if re.fullmatch(r"\d{3,4}", title):
        return True
    if re.search(
        r"(language|people|Empire|dynasty|Development Corporation|Department of|"
        r"Ministry of|Standard Time)$",
        title,
    ):
        return True
    return title.startswith(("Portal:", "Wikipedia:", "File:", "Template:"))


def is_place_collection(title: str) -> bool:
    name = cat_name(title)
    if re.search(r"\b(films?|albums?|songs?|novels?|people|biography)\b", name, re.I):
        return False
    if re.search(r"\b(list|lists)\b", name, re.I):
        return True
    return bool(re.search(r"\b(by|in|of)\b", name, re.I))


def acceptable_page(title: str) -> bool:
    if title.startswith(("List ", "Lists ", "Index ", "Outline ", "Timeline ")):
        return False
    if title.endswith("(disambiguation)"):
        return False
    blocked = (
        "(film)",
        "(album)",
        "(song)",
        "(novel)",
        "(TV series)",
        "(company)",
        "(band)",
        "(actor)",
        "(actress)",
    )
    return not any(marker in title for marker in blocked)


def api_get(base: str, params: dict[str, str]) -> dict:
    query = dict(params)
    query.setdefault("format", "json")
    url = base + "?" + urllib.parse.urlencode(query)
    delay = 1.0
    last_error: Exception | None = None
    for _ in range(6):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = json.load(response)
            if isinstance(payload, dict) and payload.get("error", {}).get("code") == "maxlag":
                time.sleep(delay)
                delay = min(delay * 2, 30)
                continue
            return payload
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(delay)
            delay = min(delay * 2, 30)
    raise RuntimeError(f"Request failed: {url}") from last_error


def category_members(title: str) -> list[dict]:
    members: list[dict] = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": title,
        "cmlimit": "500",
        "cmtype": "page|subcat",
        "maxlag": "5",
    }
    while True:
        data = api_get("https://en.wikipedia.org/w/api.php", params)
        members.extend(data.get("query", {}).get("categorymembers", []))
        cont = data.get("continue")
        if not cont:
            return members
        params = {**params, **cont}
        time.sleep(0.02)


def clean_wiki(text: str) -> str:
    text = re.sub(r"<ref[^>]*>.*?</ref>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<ref[^>]*/>", " ", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]|#]+)\]\]", r"\1", text)
    text = re.sub(r"\{\{[^{}]*\}\}", " ", text)
    text = re.sub(r"''+", "", text)
    text = text.replace("[[", " ").replace("]]", " ")
    return " ".join(text.replace("_", " ").split()).strip(" .")


def list_page_places(title: str) -> tuple[list[str], list[dict]]:
    """Bullet and table links, plus unlinked monument names from ASI list rows."""
    data = api_get(
        "https://en.wikipedia.org/w/api.php",
        {
            "action": "parse",
            "page": title,
            "prop": "wikitext",
            "redirects": "1",
            "maxlag": "5",
        },
    )
    wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
    if not wikitext:
        return [], []
    links: list[str] = []
    for line in wikitext.splitlines():
        if re.match(r"\s*\|\s*[A-Za-z][\w ]*\s*=", line):
            continue
        if not re.match(r"\s*[*#|]", line):
            continue
        for match in re.finditer(r"\[\[([^\]|#]+)", line):
            link = match.group(1).replace("_", " ").strip()
            if not link or ":" in link:
                continue
            if link[0].islower():
                link = link[0].upper() + link[1:]
            links.append(link)
    plains: list[dict] = []
    for block in re.findall(r"\{\{ASI Monument row\b(.*?)\n\}\}", wikitext, flags=re.S):
        description = re.search(r"\|\s*description\s*=\s*(.*)", block)
        location = re.search(r"\|\s*location\s*=\s*(.*)", block)
        if not description:
            continue
        name = clean_wiki(description.group(1))
        where = clean_wiki(location.group(1)) if location else ""
        if 3 <= len(name) <= 140:
            plains.append({"name": name, "location": where})
    return links, plains


def crawl() -> tuple[dict[str, dict], list[dict]]:
    if CRAWL_CACHE.is_file() and os.environ.get("PLACES_USE_CACHE") == "1":
        raw = json.loads(CRAWL_CACHE.read_text(encoding="utf-8"))
        pages = {
            title: {"states": set(meta["states"]), "cats": set(meta["cats"])}
            for title, meta in raw.items()
        }
        print(f"Loaded {len(pages)} cached pages", flush=True)
        return pages, []
    pages: dict[str, dict] = {}
    synthetics: list[dict] = []
    seen: set[str] = set()
    expanded_lists: set[str] = set()
    list_queue: list[tuple[str, str | None]] = []

    def add_page(title: str, state: str | None, via: str) -> None:
        if is_list_title(title):
            if should_expand_list(title):
                list_queue.append((title, inherited_list_state(title, state)))
            return
        if not acceptable_page(title) or boring_link(title):
            return
        slot = pages.setdefault(title, {"states": set(), "cats": set()})
        if state:
            slot["states"].add(state)
        slot["cats"].add(via)

    def drain_lists() -> None:
        while list_queue:
            title, state = list_queue.pop()
            if title in expanded_lists:
                continue
            expanded_lists.add(title)
            if len(expanded_lists) > 800:
                print("  list expansion cap reached", flush=True)
                list_queue.clear()
                return
            print(f"  list {title}", flush=True)
            links, plains = list_page_places(title)
            for link in links:
                add_page(link, state_from_text(link) or state, title)
            if state:
                for plain in plains:
                    synthetics.append({**plain, "state": state, "via": title})

    def walk(title: str, state: str | None, depth: int) -> None:
        if title in seen or depth > 8:
            return
        seen.add(title)
        if should_skip_category(title):
            return
        inferred = state_from_text(cat_name(title)) or state
        if len(seen) % 200 == 0:
            print(f"  categories walked: {len(seen)}; pages: {len(pages)}", flush=True)
        if is_place_collection(title):
            for member in category_members(title):
                if member["ns"] == 14:
                    walk(member["title"], inferred, depth + 1)
                elif member["ns"] == 0:
                    add_page(member["title"], inferred, title)
            drain_lists()
            return
        article = cat_name(title)
        if ":" not in article:
            add_page(article, inferred, title)

    for seed in SEEDS:
        print(f"Seed {seed}", flush=True)
        walk(seed, None, 0)
        drain_lists()
    print(
        f"Crawl done: {len(seen)} categories, {len(expanded_lists)} lists, {len(pages)} pages",
        flush=True,
    )
    CRAWL_CACHE.write_text(
        json.dumps(
            {
                title: {"states": sorted(meta["states"]), "cats": sorted(meta["cats"])}
                for title, meta in pages.items()
            }
        ),
        encoding="utf-8",
    )
    return pages, synthetics


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def fetch_wikipedia(titles: list[str]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for batch in chunked(titles, 40):
        data = api_get(
            "https://en.wikipedia.org/w/api.php",
            {
                "action": "query",
                "titles": "|".join(batch),
                "prop": "pageprops|coordinates",
                "ppprop": "wikibase_item|disambiguation",
                "coprop": "type|region|country",
                "colimit": "1",
                "redirects": "1",
                "maxlag": "5",
            },
        )
        query = data.get("query", {})
        redirect_to: dict[str, str] = {}
        for item in query.get("redirects", []):
            redirect_to[item["from"]] = item["to"]
        normalized = {item["from"]: item["to"] for item in query.get("normalized", [])}
        by_title = {page["title"]: page for page in query.get("pages", {}).values()}
        for original in batch:
            title = normalized.get(original, original)
            title = redirect_to.get(title, title)
            page = by_title.get(title)
            if not page or "missing" in page:
                continue
            if "disambiguation" in page.get("pageprops", {}):
                continue
            coords = None
            for coord in page.get("coordinates") or []:
                if coord.get("globe") and coord.get("globe") != "earth":
                    continue
                coords = coord
                break
            found[original] = {
                "title": page["title"],
                "qid": page.get("pageprops", {}).get("wikibase_item"),
                "wiki_coord": coords,
            }
        time.sleep(0.02)
    return found


def claim_values(entity: dict, pid: str) -> list:
    values = []
    for claim in entity.get("claims", {}).get(pid, []):
        if claim.get("rank") == "deprecated":
            continue
        snak = claim.get("mainsnak", {})
        if snak.get("snaktype") != "value":
            continue
        rank = 0 if claim.get("rank") == "preferred" else 1
        values.append((rank, snak["datavalue"]["value"]))
    values.sort(key=lambda item: item[0])
    return [value for _, value in values]


def fetch_entities(qids: list[str]) -> dict[str, dict]:
    entities: dict[str, dict] = {}
    unique = [qid for qid in dict.fromkeys(qids) if qid]
    for batch in chunked(unique, 50):
        data = api_get(
            "https://www.wikidata.org/w/api.php",
            {
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "labels|descriptions|claims",
                "languages": "en",
            },
        )
        for qid, entity in data.get("entities", {}).items():
            if "missing" not in entity:
                entities[qid] = entity
        time.sleep(0.02)
    return entities


def entity_label(entity: dict) -> str:
    return entity.get("labels", {}).get("en", {}).get("value", "")


def entity_description(entity: dict) -> str:
    return entity.get("descriptions", {}).get("en", {}).get("value", "")


def in_india(lat: float, lon: float) -> bool:
    return 6 <= lat <= 37 and 68 <= lon <= 98


def article(kind: str) -> str:
    word = kind.split()[0] if kind else ""
    if re.match(r"^(unesco|union|university|unique|uniform|unit|user|european)\b", word, re.I):
        return "a"
    return "an" if word[:1].lower() in "aeiou" else "a"


def compose_description(name: str, state: str, wd_desc: str, type_labels: list[str]) -> str:
    desc = " ".join((wd_desc or "").split()).strip(" .")
    usable = desc and "disambiguation" not in desc.lower() and "wikimedia" not in desc.lower()
    if usable:
        clause = bool(
            re.search(
                r"\b(is|was|are|were|has|have|belonged|located|dedicated|situated|built|known)\b",
                desc,
                re.I,
            )
        )
        name_in_desc = name.lower() in desc.lower()
        if desc.lower().startswith(name.lower()) or (clause and name_in_desc) or (clause and len(desc) > 90):
            text = desc[0].upper() + desc[1:]
            if not text.endswith("."):
                text += "."
            return text[:500]
        noun = re.sub(r"^(a|an|the)\s+", "", desc, flags=re.I)
        if noun and not (len(noun) > 1 and noun[0].isupper() and noun[1].isupper()):
            noun = noun[0].lower() + noun[1:]
        noun = noun or "tourism place"
        return f"{name} is {article(noun)} {noun}."[:500]
    kind = "tourism place"
    for label in type_labels:
        low = label.lower()
        if "wikimedia" in low or low in {"human", "village", "city", "town", "district"}:
            continue
        kind = label
        break
    kind_l = kind[0].lower() + kind[1:] if kind else "tourism place"
    return f"{name} is {article(kind_l)} {kind_l} in {state}, India."


NON_TOURISM_RE = re.compile(
    r"stadium|shopping mall|multiplex|cineplex|research institute|eparchy|diocese|"
    r"sports complex|sports venue|cricket ground|field hockey|recurring event|annual fair|"
    r"overview of|list article|\blist of\b|\blists of\b|\bis a list\b|"
    r"university|\bcollege\b|\bschool\b|hospital|railway station|\bairport\b|"
    r"former district|\bis a human\b|\bis a person\b|\bis a writer\b|\bis a politician\b|"
    r"\bis an event\b|\bis a building\b|\bis a street\b|\bis a road\b",
    re.I,
)
TOURISM_HINT_RE = re.compile(
    r"fort|temple|gurdwara|gurudwara|palace|museum|beach|\bpark\b|waterfall|\bfalls\b|"
    r"cave|\blake\b|church|cathedral|mosque|monastery|tomb|memorial|monument|"
    r"sanctuary|wildlife|island|garden|bazaar|market|lighthouse|view ?point|haveli|"
    r"mahal|mandir|dargah|stupa|ashram|ghat|valley|peak|\bpass\b|\bzoo\b|minar|"
    r"pillar|sarai|heritage|unesco|pilgrimage|shrine|basilica|synagogue|vihara|"
    r"chaitya|stepwell|baoli|\bkund\b|glacier|desert|forest|\bhill\b|coast|\bcape\b|"
    r"hot spring|fortress|citadel|qila|garh\b|masjid|kovil|deul|basadi|gompa|"
    r"pagoda|boat house|baradari|trek",
    re.I,
)
LIST_NAME_RE = re.compile(
    r"^(Tourist attractions|Temples|Mosques|Forts|Beaches|Lakes|Museums|Palaces|"
    r"Monuments|Caves|Waterfalls|National parks|Wildlife sanctuaries|Hill stations)"
    r" (in|of)\b",
    re.I,
)


def is_tourism_record(name: str, description: str) -> bool:
    if name in STATES or name in {
        "1984 anti-Sikh riots",
        "Independence Day (India)",
        "South India",
    }:
        return False
    if re.search(r"unnamed|<br|\[\[|\{\{", name, re.I):
        return False
    if re.match(r"^All (ancient|mounds|structures|buildings)\b", name, re.I):
        return False
    if re.search(r"\bstadium\b", name, re.I) and not re.search(
        r"tomb|fort|temple|mosque|gurdwara", name, re.I
    ):
        return False
    if LIST_NAME_RE.search(name):
        return False
    if re.search(
        r"\b(district|tehsil|taluk|municipal corporation|police|expressway|"
        r"highway|road network|railway zone|department)\b",
        name,
        re.I,
    ):
        return False
    if re.search(
        r"\bis an? (municipal|police|government|civic|highway|state government|"
        r"census|election|elections|dialect|language|agency|decoration|company|"
        r"software|concept)\b",
        description,
        re.I,
    ):
        return False
    text = f"{name} {description}"
    if NON_TOURISM_RE.search(text) and not TOURISM_HINT_RE.search(name):
        return False
    return True


def repair_description(description: str) -> str:
    description = re.sub(r"\ban uNESCO\b", "a UNESCO", description)
    description = re.sub(r"\ban union\b", "a union", description)
    description = re.sub(r"\ban university\b", "a university", description)
    description = re.sub(r"\ban unique\b", "a unique", description)
    match = re.match(
        r"^(?P<head>.+?) is (?:a|an) (?:a|an|the) (?P<rest>.+)$",
        description,
    )
    if not match:
        return description
    rest = match.group("rest").strip()
    head = match.group("head")
    if re.search(
        r"\b(is|was|are|were|belonged|located|dedicated|situated|built|known)\b",
        rest,
        re.I,
    ):
        text = rest[0].upper() + rest[1:]
        return text if text.endswith(".") else text + "."
    if re.match(r"^.+ is (?:a|an) the ", description):
        text = f"{head} is the {rest}"
    else:
        text = f"{head} is {article(rest)} {rest}"
    return text if text.endswith(".") else text + "."


def _category_from_text(text: str) -> str | None:
    lowered = text.lower()
    religious = any(
        key in lowered
        for key in (
            "temple",
            "mosque",
            "gurdwara",
            "gurudwara",
            "church",
            "monastery",
            "stupa",
            "dargah",
            "shrine",
            "pilgrimage",
            "basilica",
            "cathedral",
            "synagogue",
            "ashram",
            "mandir",
            "masjid",
            "gompa",
        )
    )
    built = any(
        key in lowered
        for key in (
            "fort",
            "palace",
            "museum",
            "mausoleum",
            "monument",
            "memorial",
            "archaeological",
            "tomb",
            "haveli",
            "stepwell",
            "minar",
            "heritage",
        )
    )
    if any(
        key in lowered
        for key in (
            "national park",
            "wildlife sanctuary",
            "tiger reserve",
            "bird sanctuary",
            "biosphere",
            "elephant reserve",
            "zoo",
        )
    ):
        return "wildlife"
    if "beach" in lowered:
        return "beach"
    if "hill station" in lowered:
        return "hill-station"
    if religious and not any(key in lowered for key in ("fort", "palace", "museum", "mausoleum")):
        return "spiritual"
    if built:
        return "heritage"
    if religious:
        return "spiritual"
    if any(
        key in lowered
        for key in (
            "waterfall",
            "falls",
            "lake",
            "cave",
            "valley",
            "mountain",
            "peak",
            "island",
            "garden",
            "river",
            "dam",
            "reservoir",
            "wetland",
            "ghat",
            "glacier",
            "desert",
            "forest",
            "view point",
            "viewpoint",
            "trek",
        )
    ):
        return "nature"
    if any(key in lowered for key in ("village", "hamlet", "hidden", "offbeat")):
        return "offbeat"
    return None


def assign_category(name: str, description: str, type_labels: list[str], cats: list[str]) -> str:
    primary = _category_from_text(" ".join([name, description, *type_labels]))
    if primary:
        return primary
    return _category_from_text(" ".join(cats)) or "other"


def assign_tags(blob: str) -> list[str]:
    lowered = blob.lower()
    tags = []
    for tag, keys in TAG_RULES:
        if any(key in lowered for key in keys):
            tags.append(tag)
    return tags[:6]


def iso_state(region: str | None) -> str | None:
    if not region:
        return None
    code = region.upper().removeprefix("IN-").strip()
    return ISO_REGION.get(code)


def wikidata_state(entity: dict | None, entities: dict[str, dict]) -> str | None:
    if not entity:
        return None
    seen: set[str] = set()
    frontier = [value["id"] for value in claim_values(entity, "P131") if "id" in value]
    for _ in range(6):
        next_frontier: list[str] = []
        for qid in frontier:
            if qid in seen:
                continue
            seen.add(qid)
            if qid in STATE_QIDS:
                return STATE_QIDS[qid]
            parent = entities.get(qid)
            if not parent:
                continue
            for value in claim_values(parent, "P131"):
                parent_id = value.get("id")
                if parent_id:
                    next_frontier.append(parent_id)
        frontier = next_frontier
        if not frontier:
            break
    return None


def resolve_states(
    page_states: set[str],
    entity: dict | None,
    entities: dict[str, dict],
    wiki_coord: dict | None,
) -> str | None:
    # Wikidata's administrative chain wins when a list page stamped the wrong state.
    located = wikidata_state(entity, entities)
    if located:
        return located
    if len(page_states) == 1:
        return next(iter(page_states))
    if len(page_states) > 1:
        return sorted(page_states)[0]
    if wiki_coord:
        return iso_state(wiki_coord.get("region"))
    return None


def is_non_place(type_labels: list[str]) -> bool:
    if not type_labels:
        return False
    if any(PLACE_RE.search(label) for label in type_labels):
        return False
    return any(NON_PLACE_RE.search(label) for label in type_labels)


MONTHS = (
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

UNITS = {
    "Q11573": "m",
    "Q828224": "km",
    "Q25343": "m²",
    "Q712226": "km²",
    "Q35852": "ha",
    "Q174728": "cm",
}

FACT_ENTITY_PROPS = (
    "P1435",
    "P149",
    "P84",
    "P112",
    "P170",
    "P206",
    "P706",
    "P825",
    "P140",
    "P361",
    "P138",
    "P127",
)


def ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def format_time(value: dict) -> str | None:
    raw = str(value.get("time") or "")
    match = re.match(r"^[+-]0*(\d+)-(\d{2})-(\d{2})", raw)
    if not match:
        return None
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    if year < 1 or year > 2100:
        return None
    precision = int(value.get("precision") or 9)
    if precision >= 11 and month and day:
        return f"{day} {MONTHS[month]} {year}"
    if precision == 10 and 1 <= month <= 12:
        return f"{MONTHS[month]} {year}"
    if precision <= 7:
        century = (year - 1) // 100 + 1
        return f"the {ordinal(century)} century"
    if precision == 8:
        return f"the {year}s"
    return str(year)


def format_quantity(value: dict) -> str | None:
    try:
        amount = float(value["amount"])
    except (KeyError, TypeError, ValueError):
        return None
    unit = str(value.get("unit") or "").rsplit("/", 1)[-1]
    if unit == "Q25343" and abs(amount) >= 1_000_000:
        amount = amount / 1_000_000
        unit = "Q712226"
    if unit not in UNITS:
        return None
    label = UNITS[unit]
    if abs(amount) >= 100:
        text = f"{amount:,.0f}"
    elif abs(amount) >= 10:
        text = f"{amount:.1f}".rstrip("0").rstrip(".")
    else:
        text = f"{amount:.2f}".rstrip("0").rstrip(".")
    return f"{text} {label}".strip()


def entity_qid_label(qid: str | None, entities: dict[str, dict]) -> str | None:
    if not qid:
        return None
    entity = entities.get(qid)
    if not entity:
        return None
    label = entity_label(entity).strip()
    return label or None


def add_fact(facts: list[str], description: str, text: str) -> None:
    cleaned = " ".join(text.split()).strip()
    if not cleaned.endswith("."):
        cleaned += "."
    if len(cleaned) < 10 or len(cleaned) > 240:
        return
    if cleaned in facts:
        return
    if cleaned.lower().strip(".") in description.lower():
        return
    facts.append(cleaned)


def build_facts(
    name: str,
    state: str,
    category: str,
    description: str,
    entity: dict | None,
    entities: dict[str, dict],
) -> list[str]:
    facts: list[str] = []
    if entity:
        opened = claim_values(entity, "P571")
        if opened:
            when = format_time(opened[0]) if isinstance(opened[0], dict) else None
            if when:
                add_fact(facts, description, f"Dates from {when}")
        official = claim_values(entity, "P1619")
        if official:
            when = format_time(official[0]) if isinstance(official[0], dict) else None
            if when and f"Dates from {when}." not in facts:
                add_fact(facts, description, f"Opened in {when}")
        for value in claim_values(entity, "P1435")[:2]:
            label = entity_qid_label(value.get("id") if isinstance(value, dict) else None, entities)
            if label:
                add_fact(facts, description, f"Recognised as {label}")
        for value in claim_values(entity, "P149")[:1]:
            label = entity_qid_label(value.get("id") if isinstance(value, dict) else None, entities)
            if label and "of india" not in label.lower() and label.lower() not in {
                "architecture",
                "architectural style",
            }:
                add_fact(facts, description, f"Built in the {label} style")
        for prop, template in (
            ("P84", "Architect: {label}"),
            ("P112", "Founded by {label}"),
            ("P170", "Created by {label}"),
            ("P825", "Dedicated to {label}"),
            ("P140", "Associated with {label}"),
            ("P138", "Named after {label}"),
            ("P206", "Set beside {label}"),
            ("P706", "Set on {label}"),
            ("P361", "Part of {label}"),
        ):
            for value in claim_values(entity, prop)[:1]:
                label = entity_qid_label(value.get("id") if isinstance(value, dict) else None, entities)
                if label and label not in {name, state, "India"}:
                    add_fact(facts, description, template.format(label=label))
        for value in claim_values(entity, "P127")[:1]:
            label = entity_qid_label(value.get("id") if isinstance(value, dict) else None, entities)
            if label and label not in {name, state, "India", "Government of India"}:
                add_fact(facts, description, f"Maintained under {label}")
        elevation = claim_values(entity, "P2044")
        if elevation and isinstance(elevation[0], dict):
            amount = format_quantity(elevation[0])
            if amount:
                add_fact(facts, description, f"Stands at about {amount} elevation")
        area = claim_values(entity, "P2046")
        if area and isinstance(area[0], dict):
            amount = format_quantity(area[0])
            if amount:
                add_fact(facts, description, f"Covers about {amount}")
        height = claim_values(entity, "P2048")
        if height and isinstance(height[0], dict):
            amount = format_quantity(height[0])
            if amount:
                add_fact(facts, description, f"Rises about {amount}")
        visitors = claim_values(entity, "P1174")
        if visitors and isinstance(visitors[0], dict):
            try:
                visits = float(visitors[0]["amount"])
            except (KeyError, TypeError, ValueError):
                visits = None
            if visits and visits > 0:
                add_fact(facts, description, f"About {visits:,.0f} visits in a recorded year")
        for value in claim_values(entity, "P131"):
            label = entity_qid_label(value.get("id") if isinstance(value, dict) else None, entities)
            if label and label not in {state, "India", name}:
                add_fact(facts, description, f"Lies in {label}, {state}")
                break
    if not facts:
        pretty = {
            "heritage": "heritage",
            "nature": "nature",
            "spiritual": "spiritual",
            "beach": "beach",
            "hill-station": "hill-station",
            "wildlife": "wildlife",
            "offbeat": "offbeat",
            "other": "tourism",
        }[category]
        add_fact(facts, description, f"Known as a {pretty} destination in {state}")
    return facts[:6]


def build_records(pages: dict[str, dict], synthetics: list[dict] | None = None) -> list[dict]:
    print(f"Fetching Wikipedia metadata for {len(pages)} pages", flush=True)
    wiki = fetch_wikipedia(list(pages))
    qids = [item["qid"] for item in wiki.values() if item.get("qid")]
    print(f"Fetching Wikidata for {len(set(qids))} items", flush=True)
    entities = fetch_entities(qids)

    admin_ids: list[str] = []
    for entity in entities.values():
        for value in claim_values(entity, "P131"):
            qid = value.get("id")
            if qid and qid not in STATE_QIDS:
                admin_ids.append(qid)
    print(f"Resolving {len(set(admin_ids))} administrative parents", flush=True)
    pending = [qid for qid in dict.fromkeys(admin_ids) if qid not in entities]
    for _ in range(5):
        if not pending:
            break
        parents = fetch_entities(pending)
        entities.update(parents)
        next_pending: list[str] = []
        for entity in parents.values():
            qid = entity.get("id")
            if qid in STATE_QIDS:
                continue
            for value in claim_values(entity, "P131"):
                parent_id = value.get("id")
                if parent_id and parent_id not in entities and parent_id not in STATE_QIDS:
                    next_pending.append(parent_id)
        pending = list(dict.fromkeys(next_pending))

    type_ids: list[str] = []
    for entity in entities.values():
        for value in claim_values(entity, "P31"):
            if value.get("id"):
                type_ids.append(value["id"])
    missing_types = [qid for qid in dict.fromkeys(type_ids) if qid not in entities]
    if missing_types:
        print(f"Fetching {len(missing_types)} type labels", flush=True)
        entities.update(fetch_entities(missing_types))

    fact_ids: list[str] = []
    place_entities = [entities[qid] for qid in dict.fromkeys(qids) if qid in entities]
    for entity in place_entities:
        for prop in (*FACT_ENTITY_PROPS, "P131"):
            for value in claim_values(entity, prop):
                fact_qid = value.get("id") if isinstance(value, dict) else None
                if fact_qid and fact_qid not in entities:
                    fact_ids.append(fact_qid)
    fact_ids = list(dict.fromkeys(fact_ids))
    if fact_ids:
        print(f"Fetching {len(fact_ids)} fact labels", flush=True)
        entities.update(fetch_entities(fact_ids))

    used_ids: set[str] = set()
    by_key: dict[tuple[str, str], dict] = {}

    def remember(record: dict) -> None:
        key = (slug(record["name"]) or record["id"], record["state"])
        current = by_key.get(key)
        if current is None:
            by_key[key] = record
            return
        current_score = (
            1 if "coordinates" in current else 0,
            len(current.get("facts") or []),
            len(current["description"]),
        )
        new_score = (
            1 if "coordinates" in record else 0,
            len(record.get("facts") or []),
            len(record["description"]),
        )
        winner, loser = (record, current) if new_score > current_score else (current, record)
        merged = dict(winner)
        facts: list[str] = []
        for fact in (winner.get("facts") or []) + (loser.get("facts") or []):
            if fact not in facts:
                facts.append(fact)
        if facts:
            merged["facts"] = facts[:6]
        if "coordinates" not in merged and "coordinates" in loser:
            merged["coordinates"] = loser["coordinates"]
        if loser["id"] in SEED_IDS:
            merged["id"] = loser["id"]
            merged["description"] = loser["description"]
            merged["category"] = loser["category"]
            if loser.get("tags"):
                merged["tags"] = loser["tags"]
        by_key[key] = merged

    for seed in SEED_RECORDS:
        remember(seed)
        used_ids.add(seed["id"])

    for plain in synthetics or []:
        name = plain["name"]
        state = plain["state"]
        if not is_tourism_record(name, name) or boring_link(name):
            continue
        location = plain.get("location") or ""
        description = f"{name} is a protected monument in {state}, India."
        facts = ["Recognised as a State Protected Monument."]
        if location and location.lower() not in {name.lower(), state.lower()}:
            fact = f"Lies in {location}, {state}."
            if 10 <= len(fact) <= 240:
                facts.append(fact)
        record = {
            "id": unique_id(name, state, None, used_ids),
            "name": name,
            "state": state,
            "category": assign_category(name, description, [], [plain.get("via", "")]),
            "description": description,
            "facts": facts,
            "tags": ["lesser-known", "state-protected"],
        }
        remember(record)

    for original, meta in pages.items():
        info = wiki.get(original)
        if not info:
            continue
        name = info["title"].replace("_", " ")
        entity = entities.get(info.get("qid") or "")
        type_labels: list[str] = []
        wd_desc = ""
        lat = lon = None
        if entity:
            wd_desc = entity_description(entity)
            if entity_label(entity) and not re.search(r"[\u0900-\u0dff]", name):
                # Prefer the Wikidata English label when the page title is only a qualifier.
                pass
            for value in claim_values(entity, "P31"):
                type_entity = entities.get(value.get("id", ""))
                if type_entity:
                    label = entity_label(type_entity)
                    if label:
                        type_labels.append(label)
            if is_non_place(type_labels):
                continue
            for value in claim_values(entity, "P625"):
                if "latitude" in value and "longitude" in value:
                    lat = float(value["latitude"])
                    lon = float(value["longitude"])
                    break
        wiki_coord = info.get("wiki_coord")
        if (lat is None or lon is None) and wiki_coord:
            lat = float(wiki_coord["lat"])
            lon = float(wiki_coord["lon"])
            country = (wiki_coord.get("country") or "").upper()
            if country and country not in {"IN", "INDIA"}:
                continue
        state = resolve_states(set(meta["states"]), entity, entities, wiki_coord)
        if not state:
            continue
        coordinates = None
        if lat is not None and lon is not None and in_india(lat, lon):
            coordinates = {"lat": round(lat, 5), "lon": round(lon, 5)}
        blob = " ".join([name, wd_desc, *type_labels, *meta["cats"]])
        description = compose_description(name, state, wd_desc, type_labels)
        if len(description) < 10 or not is_tourism_record(name, description):
            continue
        record = {
            "id": unique_id(name, state, info.get("qid"), used_ids),
            "name": name,
            "state": state,
            "category": assign_category(name, description, type_labels, list(meta["cats"])),
            "description": description,
        }
        if coordinates:
            record["coordinates"] = coordinates
        tags = assign_tags(blob)
        source = " ".join(meta["cats"])
        if re.search(r"hidden|offbeat", source, re.I) and "hidden-gem" not in tags:
            tags.append("hidden-gem")
        if re.search(r"lesser|state protected|little-known", source, re.I) and "lesser-known" not in tags:
            tags.append("lesser-known")
        if tags:
            record["tags"] = tags[:8]
        record["facts"] = build_facts(name, state, record["category"], description, entity, entities)
        remember(record)

    records = list(by_key.values())
    # Reassign ids after dedupe so dropped duplicates do not leave gaps that matter,
    # while preserved seed ids stay stable.
    final_used: set[str] = set()
    finalized = []
    for record in sorted(records, key=lambda item: (item["state"], item["name"], item["id"])):
        if record["id"] in SEED_IDS and record["id"] not in final_used:
            final_used.add(record["id"])
        elif record["id"] in final_used or not re.fullmatch(r"[a-z0-9-]+", record["id"]):
            record = dict(record)
            record["id"] = unique_id(record["name"], record["state"], None, final_used)
        else:
            final_used.add(record["id"])
        finalized.append(record)
    return finalized


SEED_IDS = {record["id"] for record in SEED_RECORDS}


def unique_id(name: str, state: str, qid: str | None, used: set[str]) -> str:
    base = slug(name) or (slug(qid) if qid else "") or "place"
    state_part = slug(state)
    candidate = f"{base}-{state_part}" if state_part else base
    if candidate not in used:
        used.add(candidate)
        return candidate
    suffix = slug(qid) if qid else "alt"
    candidate = f"{base}-{state_part}-{suffix}".strip("-")
    number = 2
    while candidate in used:
        candidate = f"{base}-{state_part}-{suffix}-{number}"
        number += 1
    used.add(candidate)
    return candidate


def write_records(records: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[dict]] = {}
    for record in records:
        grouped.setdefault(record["state"], []).append(record)
    written: set[str] = set()
    for state in STATES:
        state_records = sorted(grouped.get(state, []), key=lambda item: item["id"])
        if not state_records:
            print(f"WARNING: no places for {state}", flush=True)
            continue
        path = DATA_DIR / f"{slug(state)}.json"
        payload = json.dumps(state_records, indent=2, ensure_ascii=False) + "\n"
        path.write_text(payload, encoding="utf-8")
        written.add(path.name)
        print(f"{state}: {len(state_records)}", flush=True)
    for path in DATA_DIR.glob("*.json"):
        if path.name not in written:
            path.unlink()
    with_facts = sum(1 for record in records if record.get("facts"))
    print(
        f"Wrote {len(records)} places across {len(written)} files "
        f"({with_facts} with facts).",
        flush=True,
    )


def main() -> int:
    pages, synthetics = crawl()
    print(f"Unlinked list rows: {len(synthetics)}", flush=True)
    records = build_records(pages, synthetics)
    write_records(records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
