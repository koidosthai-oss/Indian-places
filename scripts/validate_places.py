#!/usr/bin/env python3
"""Validate place arrays against data/schema.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "data" / "schema.json"


def default_paths() -> list[Path]:
    paths = [ROOT / "data" / "places.json"]
    incoming = ROOT / "data" / "incoming"
    if incoming.is_dir():
        paths.extend(sorted(incoming.glob("*.json")))
    return [p for p in paths if p.is_file()]


def validate_file(path: Path, validator: jsonschema.Draft202012Validator) -> int:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"{path}: expected a JSON array")
    for index, record in enumerate(records):
        errors = sorted(validator.iter_errors(record), key=lambda e: e.path)
        if errors:
            lines = [f"{path}[{index}]: validation failed"]
            lines.extend(f"  - {err.message}" for err in errors)
            raise ValueError("\n".join(lines))
    return len(records)


def main() -> int:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    paths = [Path(p) for p in sys.argv[1:]] if len(sys.argv) > 1 else default_paths()
    paths = [p for p in paths if p.is_file()]

    if not paths:
        print("No place JSON files to validate.", file=sys.stderr)
        return 1

    total = 0
    try:
        for path in paths:
            total += validate_file(path, validator)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Validated {total} place(s) in {len(paths)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
