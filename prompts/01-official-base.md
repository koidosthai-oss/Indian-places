# Prompt: Load official base for one district

Using official sources (Census 2011 village lists, LGD, OSM Overpass, or free APIs like india-location-hub.in), collect every village and town in [DISTRICT], [STATE].

Output clean JSON array matching data/schema.json.
- Strictly assign only places that belong to this district.
- Include coordinates when available.
- Tag type appropriately.
- Skip any already present in data/places.json.
- After writing, update data/coverage.json for this district (status: partial or complete, places_count, last_updated).

Save to data/incoming/[district_slug].json then merge into master.
