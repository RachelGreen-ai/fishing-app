#!/usr/bin/env python3
"""Create reproducible train/validation/test splits from a classification manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_jsonl", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--train", type=float, default=0.7)
    parser.add_argument("--validation", type=float, default=0.15)
    parser.add_argument("--test", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=20260428)
    parser.add_argument("--mode", choices=["symlink", "copy", "manifest-only"], default="symlink")
    parser.add_argument("--min-per-class", type=int, default=30)
    parser.add_argument("--labels-json", type=Path)
    parser.add_argument("--taxonomy-json", type=Path)
    return parser.parse_args()


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


def stable_image_name(row: dict) -> str:
    source_path = Path(row["source_path"])
    suffix = source_path.suffix.lower() or ".jpg"
    digest = hashlib.sha1(str(source_path).encode("utf-8")).hexdigest()[:12]
    return f"{row['image_id']}_{digest}{suffix}"


def materialize(source_path: Path, destination: Path, mode: str) -> None:
    if mode == "manifest-only":
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return

    if mode == "copy":
        shutil.copy2(source_path, destination)
    else:
        os.symlink(source_path.resolve(), destination)


def split_rows(rows: list[dict], train_fraction: float, validation_fraction: float, seed: int) -> dict[str, list[dict]]:
    by_species: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_species[row["species_id"]].append(row)

    splits = {"train": [], "validation": [], "test": []}
    rng = random.Random(seed)

    for species_id, species_rows in sorted(by_species.items()):
        species_rows = list(species_rows)
        rng.shuffle(species_rows)
        count = len(species_rows)

        train_count = int(round(count * train_fraction))
        validation_count = int(round(count * validation_fraction))
        if count >= 3:
            train_count = min(max(1, train_count), count - 2)
            validation_count = min(max(1, validation_count), count - train_count - 1)
        test_count = count - train_count - validation_count

        if test_count <= 0 and count > 0:
            test_count = 1
            train_count = max(0, train_count - 1)

        splits["train"].extend(species_rows[:train_count])
        splits["validation"].extend(species_rows[train_count : train_count + validation_count])
        splits["test"].extend(species_rows[train_count + validation_count :])

    return splits


def taxonomy_lookup(path: Path | None) -> dict[str, dict]:
    if not path:
        return {}
    return {row["id"]: row for row in load_json(path)}


def enrich_with_taxonomy(row: dict, taxonomy: dict[str, dict]) -> dict:
    enriched = dict(row)
    species_taxonomy = taxonomy.get(row["species_id"])
    if not species_taxonomy:
        return enriched

    for field in ("family", "family_common", "label_group", "lookalike_group", "taxon_rank", "is_species_level"):
        enriched[field] = species_taxonomy.get(field, enriched.get(field, ""))
    return enriched


def write_manifest(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            clean = {key: value for key, value in row.items() if not key.startswith("_")}
            handle.write(json.dumps(clean, sort_keys=True))
            handle.write("\n")


def write_subset_json(source_path: Path | None, destination_path: Path, present_species: set[str]) -> None:
    if not source_path:
        return
    rows = load_json(source_path)
    subset = [row for row in rows if row.get("id") in present_species]
    destination_path.write_text(json.dumps(subset, indent=2, sort_keys=True), encoding="utf-8")


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    args = parse_args()
    total_fraction = args.train + args.validation + args.test
    if abs(total_fraction - 1.0) > 0.001:
        raise SystemExit("train + validation + test must equal 1.0")

    source_rows = load_jsonl(args.manifest_jsonl)
    eligible_rows = [row for row in source_rows if row.get("species_id") and row.get("source_path")]
    counts = Counter(row["species_id"] for row in eligible_rows)
    skipped_species = {
        species_id: count
        for species_id, count in counts.items()
        if count < args.min_per_class
    }
    rows = [row for row in eligible_rows if row["species_id"] not in skipped_species]
    splits = split_rows(rows, args.train, args.validation, args.seed)
    present_species = {row["species_id"] for row in rows}
    taxonomy = taxonomy_lookup(args.taxonomy_json)

    args.output_root.mkdir(parents=True, exist_ok=True)
    report_counts = {}

    for split_name, split_rows_value in splits.items():
        split_manifest_rows = []
        for row in split_rows_value:
            source_path = Path(row["source_path"])
            destination = args.output_root / split_name / row["species_id"] / stable_image_name(row)
            if not source_path.exists():
                raise SystemExit(f"source image missing: {source_path}")
            materialize(source_path, destination, args.mode)
            split_manifest_row = enrich_with_taxonomy(row, taxonomy)
            split_manifest_row["split"] = split_name
            split_manifest_row["image"] = str(destination.relative_to(args.output_root))
            split_manifest_rows.append(split_manifest_row)

        write_manifest(args.output_root / f"{split_name}.manifest.jsonl", split_manifest_rows)
        report_counts[split_name] = dict(sorted(Counter(row["species_id"] for row in split_manifest_rows).items()))

    write_subset_json(args.labels_json, args.output_root / "labels.json", present_species)
    write_subset_json(args.taxonomy_json, args.output_root / "taxonomy.json", present_species)

    report = {
        "input_manifest": str(args.manifest_jsonl),
        "output_root": str(args.output_root),
        "mode": args.mode,
        "seed": args.seed,
        "fractions": {
            "train": args.train,
            "validation": args.validation,
            "test": args.test,
        },
        "skipped_species_below_minimum": skipped_species,
        "counts": report_counts,
    }
    (args.output_root / "split_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
