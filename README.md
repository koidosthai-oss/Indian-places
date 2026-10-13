# Indian-places

The comprehensive list of each and every place in India for tourism, including lesser-known places, hidden gems, and offbeat destinations.

## Development

```bash
bash scripts/cloud-agent-install.sh
.venv/bin/python scripts/validate_places.py
.venv/bin/pytest -q
```

Place records live in `data/places/*.json` and must match `schema/place.schema.json`.
