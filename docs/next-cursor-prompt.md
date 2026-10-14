# Next Cursor Agent Prompt (Roadmap Advancement)

Copy-paste into Cursor Agent (Ctrl/Cmd+I):

```text
Load the project rules and schema. Advance the India places travel portal roadmap.

1. First run the safe validation:
   bash scripts/cloud-agent-install.sh
   .venv/bin/python scripts/validate_places.py || true
   Note any failures but continue.

2. Generate a coverage summary JSON (places per state, count with coordinates, category breakdown) from data/places/*.json and save as data/coverage-summary.json.

3. Identify the next 3 high-value districts that are under-covered for tourism places (prioritize NE states or states with existing partial data).

4. For one of those districts, draft 5–10 enrichment examples (best_time, visit_duration, culture_notes, access_notes) in a separate overlay JSON so the main schema stays valid.

5. Update README.md with a short Roadmap section if needed.

Do not invent places. Keep district accuracy strict. Output the coverage summary and the next recommended district. If validation fails, list the failing records but do not block the rest of the work.
```

Run after current automation harvest or local data is synced.
