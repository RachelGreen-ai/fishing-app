#!/usr/bin/env python3
"""Report per-species image coverage for classification datasets."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


SPLITS = ("train", "validation", "test")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_or_manifest", type=Path)
    parser.add_argument("--labels-json", type=Path)
    parser.add_argument("--priority-json", type=Path)
    parser.add_argument("--priority-region")
    parser.add_argument("--target-per-class", type=int, default=800)
    parser.add_argument("--minimum-per-class", type=int, default=250)
    return parser.parse_args()


def load_json(path: Path):
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
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return rows


def manifest_paths(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    paths = [path / f"{split}.manifest.jsonl" for split in SPLITS if (path / f"{split}.manifest.jsonl").exists()]
    if paths:
        return paths
    manifest = path / "manifest.jsonl"
    if manifest.exists():
        return [manifest]
    raise SystemExit(f"No manifest JSONL found at {path}")


def load_priority(path: Path | None, region: str | None) -> dict[str, float]:
    if not path:
        return {}
    if not region:
        raise SystemExit("--priority-region is required with --priority-json")
    payload = load_json(path)
    region_payload = payload.get("regions", {}).get(region)
    if not region_payload:
        available = ", ".join(sorted(payload.get("regions", {}))) or "<none>"
        raise SystemExit(f"Priority region {region!r} not found. Available: {available}")
    return {
        str(species_id): float(weight)
        for species_id, weight in (region_payload.get("species_weights") or {}).items()
    }


def load_label_ids(path: Path | None, rows: list[dict]) -> list[str]:
    if path:
        return [row["id"] for row in load_json(path)]
    return sorted({row["species_id"] for row in rows if row.get("species_id")})


def main() -> int:
    args = parse_args()
    rows = []
    for path in manifest_paths(args.dataset_or_manifest):
        rows.extend(load_jsonl(path))

    label_ids = load_label_ids(args.labels_json, rows)
    priority = load_priority(args.priority_json, args.priority_region)
    total_counts = Counter(row["species_id"] for row in rows if row.get("species_id"))
    split_counts: dict[str, Counter] = {split: Counter() for split in SPLITS}
    for row in rows:
        split = row.get("split")
        if split in split_counts and row.get("species_id"):
            split_counts[split][row["species_id"]] += 1

    species = {}
    for species_id in label_ids:
        count = total_counts[species_id]
        target_gap = max(0, args.target_per_class - count)
        minimum_gap = max(0, args.minimum_per_class - count)
        species[species_id] = {
            "total": count,
            "train": split_counts["train"][species_id],
            "validation": split_counts["validation"][species_id],
            "test": split_counts["test"][species_id],
            "priority_weight": priority.get(species_id),
            "minimum_gap": minimum_gap,
            "target_gap": target_gap,
            "status": "target_met" if target_gap == 0 else "below_minimum" if minimum_gap else "needs_enrichment",
        }

    weak_species = [
        species_id
        for species_id, row in sorted(
            species.items(),
            key=lambda item: (item[1]["target_gap"] <= 0, -(item[1]["priority_weight"] or 0), item[1]["total"]),
        )
        if row["target_gap"] > 0
    ]

    report = {
        "dataset_or_manifest": str(args.dataset_or_manifest),
        "image_count": sum(total_counts.values()),
        "class_count": len(label_ids),
        "target_per_class": args.target_per_class,
        "minimum_per_class": args.minimum_per_class,
        "weak_species_by_priority": weak_species,
        "species": species,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
