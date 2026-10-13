# Indian-places

The comprehensive list of each and every place in India for tourism, including lesser-known places, hidden gems, and offbeat destinations.

## Development

```bash
bash scripts/cloud-agent-install.sh
.venv/bin/python scripts/validate_places.py
.venv/bin/pytest -q
```

Place records live in `data/places/<state-or-territory>.json` and must match `schema/place.schema.json`.

Regenerate the catalog from English Wikipedia tourism categories and Wikidata coordinates (descriptions are composed from Wikidata facts, not copied article text):

```bash
.venv/bin/python scripts/extract_places.py
```
