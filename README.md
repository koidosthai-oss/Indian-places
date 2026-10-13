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
```
