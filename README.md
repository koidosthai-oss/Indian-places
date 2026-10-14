# Indian-places

The comprehensive list of each and every place in India for tourism, including lesser-known places, hidden gems, and offbeat destinations.

## Development

```bash
# One-time setup or after dependency changes
bash scripts/cloud-agent-install.sh

# Validate place records (continues even if some records still need enrichment)
.venv/bin/python scripts/validate_places.py || echo "Validation reported issues — fix schema mismatches before final merge"

# Optional full test suite
.venv/bin/pytest -q
```

Place records live in `data/places/<state-or-territory>.json` and must match `schema/place.schema.json`.

Each record has a short description and a `facts` list (dates, heritage status, setting, and similar details composed from Wikidata claims). Regenerate the catalog from English Wikipedia tourism categories and list pages, plus Wikidata coordinates (article prose is not copied):

```bash
.venv/bin/python scripts/extract_places.py
.venv/bin/python scripts/merge_open_sources.py
```

`merge_open_sources.py` then adds named places from GeoNames and Wikidata, and from OpenStreetMap when the public Overpass service answers. That pass keeps mapped sites that have little or no published visitor information, including temples, forts, falls, lakes, dunes, passes, and wildlife reserves that do not have their own articles. Forest-reserve parcels, hotels, stations, and unnamed spots stay out.

## Roadmap
See `docs/` for current roadmap notes and the next Cursor agent prompt.
