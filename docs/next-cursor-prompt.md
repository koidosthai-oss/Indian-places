# Next Cursor Agent Prompt — Full Data Collection & Attractive Overlay

Copy-paste into Cursor Agent (Ctrl/Cmd+I). This is a long-running, max-extent task.

```text
Load the project rules, schema/place.schema.json, and all existing data/places/*.json files.

Goal: compile the fullest possible tourism-oriented place catalog for all of India and produce a rich overlay of interesting facts that attract visitors. Do not limit to a few districts or examples. Process every state/UT file.

Steps:

1. Run safe setup and validation:
   bash scripts/cloud-agent-install.sh
   .venv/bin/python scripts/validate_places.py || true
   Note failures but continue. Do not block on schema issues.

2. Generate a complete coverage summary across ALL states/UTs:
   - Total places per state
   - Count and percentage with coordinates
   - Category breakdown
   - Places missing facts or description quality notes
   Save as data/coverage-summary.json and also print a short table.

3. Create a full enrichment overlay for the entire dataset:
   - For every place (or as many as feasible in one pass), add or draft interesting, visitor-attracting facts.
   - Focus on: unique history, festivals, local culture, best time to visit, suggested duration, nearby food, access tips, hidden-gem character, or surprising details.
   - Keep the original data/places/*.json files schema-valid.
   - Write the enrichment into a separate overlay structure, for example data/enrichment-overlay/<state>.json or a single data/enrichment-overlay.json keyed by place id.
   - Do not invent places or coordinates. Only enrich existing records or clearly flag gaps for later collection.

4. Identify and list gaps:
   - States or districts that still look thin compared with known tourism potential.
   - Place types that are under-represented (e.g. offbeat villages, lesser-known temples, small hill spots, wildlife edges).
   - Save a gaps.json that can be used for the next collection round.
   - Keep the collection open-ended: the list is never finished.

5. Update README.md with a short note that the catalog is under continuous expansion and that enrichment overlays live in data/enrichment-overlay/.

Constraints:
- Strict district and state accuracy. Never move a place to the wrong district.
- Prefer interesting, concrete facts over generic text.
- Output progress frequently so long runs remain useful.
- At the end, summarize: total places processed, enrichment coverage percentage, top gap areas, and the exact next collection prompt you recommend for the automation.

This is a full-catalog pass, not a sample. Maximize data and attractiveness.
```

Use this prompt when you want maximum collection and fact enrichment across the whole country.
