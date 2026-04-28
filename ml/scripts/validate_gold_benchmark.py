#!/usr/bin/env python3
"""Validate a frozen golden fish-identification benchmark manifest."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


UNKNOWN_LABEL = "unknown"
REQUIRED_FIELDS = {
    "image_id",
    "image",
    "species_id",
    "scientific_name",
    "split",
    "scenario_tags",
    "region",
    "water_type",
    "quality",
    "source",
    "license",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_jsonl", type=Path)
    parser.add_argument("config_json", type=Path)
    parser.add_argument("--skip-image-check", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            row["_line"] = line_number
            rows.append(row)
    return rows


def load_label_ids(config_path: Path, config: dict) -> set[str]:
    labels_path = (config_path.parent / config["labels_file"]).resolve()
    labels = load_json(labels_path)
    return {row["id"] for row in labels}


def add_error(errors: list[str], row: dict, message: str) -> None:
    line = row.get("_line", "?")
    image_id = row.get("image_id", "<missing image_id>")
    errors.append(f"line {line} ({image_id}): {message}")


def main() -> int:
    args = parse_args()
    config = load_json(args.config_json)
    rows = load_jsonl(args.manifest_jsonl)
    label_ids = load_label_ids(args.config_json, config)

    errors: list[str] = []
    image_ids = Counter(row.get("image_id") for row in rows)
    images = Counter(row.get("image") for row in rows)
    per_species = Counter()
    scenario_counts = Counter()
    low_quality = 0
    difficult = 0
    lookalike = 0
    unknown = 0

    allowed_splits = set(config["allowed_splits"])
    quality_values = set(config["quality_values"])
    known_lookalike_groups = set(config["known_lookalike_groups"])
    manifest_root = args.manifest_jsonl.parent

    for row in rows:
        missing = sorted(REQUIRED_FIELDS - row.keys())
        if missing:
            add_error(errors, row, f"missing fields: {', '.join(missing)}")

        image_id = row.get("image_id")
        if image_id and image_ids[image_id] > 1:
            add_error(errors, row, "duplicate image_id")

        image = row.get("image")
        if image and images[image] > 1:
            add_error(errors, row, "duplicate image path")

        if image and not args.skip_image_check and not (manifest_root / image).exists():
            add_error(errors, row, f"image file does not exist: {image}")

        split = row.get("split")
        if split not in allowed_splits:
            add_error(errors, row, f"unsupported split: {split}")

        quality = row.get("quality")
        if quality not in quality_values:
            add_error(errors, row, f"unsupported quality: {quality}")

        species_id = row.get("species_id")
        if species_id == UNKNOWN_LABEL:
            unknown += 1
        elif species_id in label_ids:
            per_species[species_id] += 1
        else:
            add_error(errors, row, f"species_id not in labels: {species_id}")

        tags = row.get("scenario_tags")
        if not isinstance(tags, list) or not tags:
            add_error(errors, row, "scenario_tags must be a non-empty list")
            tags = []

        scenario_counts.update(tags)
        if quality == "low" or any(tag in tags for tag in ("poor-light", "motion-blur", "partial-fish")):
            low_quality += 1
        if any(tag in tags for tag in ("angled", "hand", "deck", "net", "poor-light", "motion-blur", "partial-fish", "multiple-fish", "juvenile")):
            difficult += 1

        lookalike_group = row.get("lookalike_group", "")
        if lookalike_group:
            if lookalike_group not in known_lookalike_groups:
                add_error(errors, row, f"unknown lookalike_group: {lookalike_group}")
            lookalike += 1

    minimum_per_species = int(config["minimum_per_species"])
    for label_id in sorted(label_ids):
        count = per_species[label_id]
        if count < minimum_per_species:
            errors.append(f"{label_id}: has {count} examples; expected at least {minimum_per_species}")

    minimum_unknown = int(config["minimum_unknown"])
    if unknown < minimum_unknown:
        errors.append(f"unknown: has {unknown} examples; expected at least {minimum_unknown}")

    total = len(rows)
    if total == 0:
        errors.append("manifest is empty")
    else:
        required_scenario_tags = set(config["required_scenario_tags"])
        missing_tags = sorted(tag for tag in required_scenario_tags if scenario_counts[tag] == 0)
        if missing_tags:
            errors.append(f"required scenario tags missing: {', '.join(missing_tags)}")

        if difficult / total < float(config["minimum_difficult_fraction"]):
            errors.append("difficult field-image fraction is below target")

        if low_quality / total < float(config["minimum_low_quality_fraction"]):
            errors.append("low-quality realistic image fraction is below target")

        if lookalike / total < float(config["minimum_lookalike_fraction"]):
            errors.append("lookalike fraction is below target")

    if errors:
        print("Gold benchmark is not ready:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        json.dumps(
            {
                "benchmark_id": config["benchmark_id"],
                "count": total,
                "known_count": sum(per_species.values()),
                "unknown_count": unknown,
                "per_species": dict(sorted(per_species.items())),
                "scenario_tags": dict(sorted(scenario_counts.items())),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
