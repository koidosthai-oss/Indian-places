#!/usr/bin/env python3
"""Validate place records under data/places against schema/place.schema.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "place.schema.json"
DATA_DIR = ROOT / "data" / "places"


def main() -> int:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    if not DATA_DIR.is_dir():
        print(f"Missing data directory: {DATA_DIR}", file=sys.stderr)
        return 1

    files = sorted(DATA_DIR.glob("*.json"))
    if not files:
        print(f"No JSON files in {DATA_DIR}", file=sys.stderr)
        return 1

    total = 0
    seen_ids: dict[str, Path] = {}
    for path in files:
        records = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            print(f"{path}: expected a JSON array", file=sys.stderr)
            return 1
        for index, record in enumerate(records):
            errors = sorted(validator.iter_errors(record), key=lambda e: e.path)
            if errors:
                print(f"{path}[{index}]: validation failed", file=sys.stderr)
                for err in errors:
                    print(f"  - {err.message}", file=sys.stderr)
                return 1
            place_id = record["id"]
            previous = seen_ids.get(place_id)
            if previous is not None:
                print(
                    f"{path}[{index}]: duplicate id {place_id} (also in {previous})",
                    file=sys.stderr,
                )
                return 1
            seen_ids[place_id] = path
            total += 1

    print(f"Validated {total} place(s) in {len(files)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
