# Next Cursor Agent Prompt (Roadmap Advancement)

Copy-paste into Cursor Agent (Ctrl/Cmd+I):

```text
Load the project rules and schema. Advance the India places travel portal roadmap.

1. Generate a coverage summary JSON (places per state, count with coordinates, category breakdown) from data/places/*.json and save as data/coverage-summary.json.
2. Identify the next 3 high-value districts that are under-covered for tourism places (prioritize NE states or states with existing partial data).
3. For one of those districts, draft 5-10 enrichment examples (add best_time, visit_duration, culture_notes, access_notes as comments or a separate enrichment overlay JSON).
4. Update README.md with a short Roadmap section pointing to docs/roadmap.md if it exists, or create a minimal one.
5. Validate any changes against schema/place.schema.json.

Do not invent places. Keep district accuracy strict. Output the coverage summary and the next recommended district.
```

Run after current automation harvest or local data is synced.
