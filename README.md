# Indian-places

The comprehensive list of each and every place in India for tourism, including lesser-known places, hidden gems, and offbeat destinations.

## Development

```bash
bash scripts/cloud-agent-install.sh
.venv/bin/python scripts/validate_places.py
.venv/bin/pytest -q
```

Place records live in `data/places/<state-or-territory>.json` and must match `schema/place.schema.json`.

Each record has a short description and a `facts` list (dates, heritage status, setting, and similar details composed from Wikidata claims). Regenerate the catalog from English Wikipedia tourism categories and list pages, plus Wikidata coordinates (article prose is not copied):

```bash
.venv/bin/python scripts/extract_places.py
.venv/bin/python scripts/merge_open_sources.py
```

`merge_open_sources.py` then adds named places from GeoNames and Wikidata, and from OpenStreetMap when the public Overpass service answers. That pass keeps mapped sites that have little or no published visitor information, including temples, forts, falls, lakes, dunes, passes, and wildlife reserves that do not have their own articles. Forest-reserve parcels, hotels, stations, and unnamed spots stay out.

The catalog is under continuous expansion. `data/coverage-summary.json` counts every state and union territory. Visitor notes that sit outside the place schema live in `data/enrichment-overlay/<state>.json`. `data/gaps.json` lists thin regions and missing themes for the next collection round. Rebuild them with:

```bash
.venv/bin/python scripts/build_catalog_overlay.py
```

Those overlay files do not add places or coordinates. A district mention is copied from the place's existing facts and is never used to move the place.

`scripts/harvest_cited_facts.py` adds visitor facts only when an official tourism page or Wikidata states them, and it stores the source URL on the overlay. A conflicting district is flagged and the original state is kept.

Open image references live in `data/picture-overlay/<state>.json`. `scripts/harvest_pictures.py` stores Wikimedia Commons file URLs only when the API metadata names a free license and the filename matches the place. Image files are not downloaded.
