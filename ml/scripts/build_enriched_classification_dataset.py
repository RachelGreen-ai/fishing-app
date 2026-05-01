#!/usr/bin/env python3
"""Build a classifier dataset from a frozen base split plus enrichment manifests."""

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
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--base-dataset-root", type=Path, required=True)
    parser.add_argument("--enrichment-manifest-jsonl", type=Path, action="append", default=[])
    parser.add_argument("--mode", choices=["symlink", "copy"], default="symlink")
    parser.add_argument("--seed", type=int, default=20260430)
    parser.add_argument("--enrichment-validation-fraction", type=float, default=0.15)
    return parser.parse_args()


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


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def stable_name(row: dict, source_path: Path) -> str:
    suffix = source_path.suffix.lower() or ".jpg"
    key = f"{row.get('source', '')}:{row.get('source_observation_id', '')}:{row.get('source_photo_id', '')}:{source_path}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"{row['image_id']}_{digest}{suffix}"


def materialize(source_path: Path, destination: Path, mode: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        return
    if mode == "copy":
        shutil.copy2(source_path, destination)
    else:
        os.symlink(source_path.resolve(), destination)


def source_path_for(row: dict, base_dataset_root: Path) -> Path:
    source_path = Path(row.get("source_path") or "")
    if source_path.exists():
        return source_path
    candidate = base_dataset_root / row["image"]
    if candidate.exists():
        return candidate
    raise SystemExit(f"Missing image for row {row.get('image_id')}: {source_path} or {candidate}")


def dedupe_key(row: dict) -> tuple[str, str]:
    source = str(row.get("source") or "")
    observation_id = row.get("source_observation_id")
    photo_id = row.get("source_photo_id")
    if source and observation_id and photo_id:
        return ("source-photo", f"{source}:{observation_id}:{photo_id}")
    if source and observation_id:
        return ("source-observation", f"{source}:{observation_id}")
    if row.get("source_path"):
        return ("source-path", str(row["source_path"]))
    return ("image-id", str(row.get("image_id") or row.get("image")))


def split_enrichment(rows: list[dict], validation_fraction: float, seed: int) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    by_species: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_species[row["species_id"]].append(row)

    splits = {"train": [], "validation": []}
    for species_rows in by_species.values():
        shuffled = list(species_rows)
        rng.shuffle(shuffled)
        validation_count = int(round(len(shuffled) * validation_fraction))
        validation_count = min(max(1, validation_count), len(shuffled) - 1)
        splits["validation"].extend(shuffled[:validation_count])
        splits["train"].extend(shuffled[validation_count:])
    return splits


def write_split_rows(args: argparse.Namespace, split: str, rows: list[dict]) -> list[dict]:
    output_rows = []
    for row in rows:
        source_path = source_path_for(row, args.base_dataset_root)
        relative_image = Path(split) / row["species_id"] / stable_name(row, source_path)
        materialize(source_path, args.output_root / relative_image, args.mode)
        output_row = dict(row)
        output_row["split"] = split
        output_row["image"] = str(relative_image)
        output_rows.append(output_row)
    write_jsonl(args.output_root / f"{split}.manifest.jsonl", output_rows)
    return output_rows


def main() -> int:
    args = parse_args()
    if not 0 < args.enrichment_validation_fraction < 1:
        raise SystemExit("--enrichment-validation-fraction must be between 0 and 1")

    base_train = load_jsonl(args.base_dataset_root / "train.manifest.jsonl")
    base_validation = load_jsonl(args.base_dataset_root / "validation.manifest.jsonl")
    base_test = load_jsonl(args.base_dataset_root / "test.manifest.jsonl")
    frozen_test_keys = {dedupe_key(row) for row in base_test}
    seen_trainval_keys = {dedupe_key(row) for row in base_train + base_validation}

    enrichment_rows = []
    counters = Counter()
    for manifest in args.enrichment_manifest_jsonl:
        for row in load_jsonl(manifest):
            key = dedupe_key(row)
            if key in frozen_test_keys:
                counters["skipped_frozen_test_overlap"] += 1
                continue
            if key in seen_trainval_keys:
                counters["skipped_base_trainval_duplicate"] += 1
                continue
            seen_trainval_keys.add(key)
            enrichment_rows.append(row)

    enrichment_splits = split_enrichment(
        enrichment_rows,
        args.enrichment_validation_fraction,
        args.seed,
    )
    train_rows = base_train + enrichment_splits["train"]
    validation_rows = base_validation + enrichment_splits["validation"]
    test_rows = base_test

    args.output_root.mkdir(parents=True, exist_ok=True)
    final_rows = {
        "train": write_split_rows(args, "train", train_rows),
        "validation": write_split_rows(args, "validation", validation_rows),
        "test": write_split_rows(args, "test", test_rows),
    }

    for filename in ("labels.json", "taxonomy.json"):
        source = args.base_dataset_root / filename
        if source.exists():
            shutil.copy2(source, args.output_root / filename)

    report = {
        "base_dataset_root": str(args.base_dataset_root),
        "output_root": str(args.output_root),
        "mode": args.mode,
        "seed": args.seed,
        "enrichment_manifests": [str(path) for path in args.enrichment_manifest_jsonl],
        "enrichment_rows": len(enrichment_rows),
        "counters": dict(counters),
        "counts": {
            split: dict(sorted(Counter(row["species_id"] for row in rows).items()))
            for split, rows in final_rows.items()
        },
        "frozen_test_manifest": str(args.base_dataset_root / "test.manifest.jsonl"),
    }
    (args.output_root / "split_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
