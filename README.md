# India Places Database — Cursor Project

Efficient setup for collecting, validating, and expanding a complete factual list of every place in India (official villages/towns + hidden gems / offbeat overlay).

## Official base layers (instant bulk coverage)
- **Census 2011**: ~590k–640k villages. Sites: villageinindia.com, villageinfo.org, data.gov.in Complete Villages Directory.
- **Local Government Directory (LGD)**: Official, more recent revenue villages/panchayats. lgdirectory.gov.in + data.gov.in APIs.
- **OpenStreetMap**: Daily Geofabrik extract (india-latest.osm.pbf ~1.6GB) or HDX populated places. Excellent for named places + coordinates.
- **Survey of India** village boundaries (partial states released).

These cover nearly all administrative places. Use research overlay only for missed / non-administrative / hidden-gem spots.

## Project structure
- `data/` — master places (`places.json`), coverage (`coverage.json`), schema (`schema.json`), district incoming batches (`incoming/`)
- `scripts/` — collection, validation, Overpass, API loaders
- `prompts/` — ready Cursor agent prompts
- `.cursor/` — Cloud Agent environment config

## How to use in Cursor (Start plan)
1. Open this folder in Cursor.
2. Add recommended MCP servers (Firecrawl / Browserless / Olostep) via Settings → MCP.
3. Use Agent mode with the prompts in `prompts/`.
4. Cloud agents for overnight district batches.
5. All data stays in local files → permanent on your computer. Commit to Git if desired.

## Permanent storage
Data lives in this folder on your machine. Cursor cloud agents write back to the same files. For extra permanence, push to a private GitHub repo.

## Development (Cloud Agents)

```bash
bash scripts/cloud-agent-install.sh
.venv/bin/python scripts/validate_places.py
.venv/bin/pytest -q
```

Place records must match `data/schema.json`. Save district batches to `data/incoming/[district_slug].json`, then merge into `data/places.json` and update `data/coverage.json`.
