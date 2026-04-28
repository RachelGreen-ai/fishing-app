#!/usr/bin/env python3
"""Validate fish label taxonomy files for hierarchy-aware ML work."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("taxonomy_json", type=Path)
    parser.add_argument("--schema", type=Path, default=Path("ml/label_taxonomy.schema.json"))
    parser.add_argument("--labels-json", type=Path)
    parser.add_argument("--aliases-json", type=Path)
    return parser.parse_args()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    args = parse_args()
    schema = load_json(args.schema)
    rows = load_json(args.taxonomy_json)
    errors: list[str] = []

    required_fields = set(schema["required_species_fields"])
    allowed_statuses = set(schema["allowed_statuses"])
    allowed_water_types = set(schema["allowed_water_types"])
    allowed_app_regions = set(schema["allowed_app_regions"])

    ids = [row.get("id") for row in rows]
    for duplicate_id, count in Counter(ids).items():
        if count > 1:
            errors.append(f"duplicate id: {duplicate_id}")

    for row in rows:
        label_id = row.get("id", "<missing id>")
        missing = sorted(required_fields - row.keys())
        if missing:
            errors.append(f"{label_id}: missing fields: {', '.join(missing)}")
            continue

        if row["status"] not in allowed_statuses:
            errors.append(f"{label_id}: unsupported status {row['status']}")

        unsupported_water = sorted(set(row["water_types"]) - allowed_water_types)
        if unsupported_water:
            errors.append(f"{label_id}: unsupported water_types: {', '.join(unsupported_water)}")

        unsupported_regions = sorted(set(row["app_regions"]) - allowed_app_regions)
        if unsupported_regions:
            errors.append(f"{label_id}: unsupported app_regions: {', '.join(unsupported_regions)}")

        if row["is_species_level"] and row["taxon_rank"] != "species":
            errors.append(f"{label_id}: species-level labels must use taxon_rank species")

        if not row["is_species_level"] and row["taxon_rank"] == "species":
            errors.append(f"{label_id}: non species-level label cannot use taxon_rank species")

        for field in ("family", "label_group", "lookalike_group"):
            if not row[field]:
                errors.append(f"{label_id}: {field} cannot be empty")

    if args.labels_json:
        labels = load_json(args.labels_json)
        label_ids = {row["id"] for row in labels}
        taxonomy_ids = {row["id"] for row in rows}
        missing_taxonomy = sorted(label_ids - taxonomy_ids)
        extra_taxonomy = sorted(taxonomy_ids - label_ids)
        if missing_taxonomy:
            errors.append(f"labels missing taxonomy: {', '.join(missing_taxonomy)}")
        if extra_taxonomy:
            errors.append(f"taxonomy ids not in labels: {', '.join(extra_taxonomy)}")

    if args.aliases_json:
        aliases = load_json(args.aliases_json)
        taxonomy_ids = {row["id"] for row in rows}
        missing_aliases = sorted(taxonomy_ids - set(aliases))
        if missing_aliases:
            errors.append(f"taxonomy ids missing aliases: {', '.join(missing_aliases)}")

    if errors:
        print("Label taxonomy is not ready:")
        for error in errors:
            print(f"- {error}")
        return 1

    by_group: dict[str, int] = defaultdict(int)
    by_family: dict[str, int] = defaultdict(int)
    for row in rows:
        by_group[row["label_group"]] += 1
        by_family[row["family"]] += 1

    print(
        json.dumps(
            {
                "count": len(rows),
                "label_groups": dict(sorted(by_group.items())),
                "families": dict(sorted(by_family.items())),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
