#!/usr/bin/env python3
"""Prepare manifests from the Kaggle large-scale fish segmentation dataset."""

from __future__ import annotations

import argparse
import json
import random
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
SKIP_DETECTION_CLASSES = {"Shrimp"}

SOURCE_CLASS_METADATA = {
    "Black Sea Sprat": {
        "common_name": "Black Sea Sprat",
        "scientific_name": "Clupeonella cultriventris",
        "taxonomy_species_id": None,
    },
    "Gilt-Head Bream": {
        "common_name": "Gilthead Seabream",
        "scientific_name": "Sparus aurata",
        "taxonomy_species_id": "gilthead-seabream",
    },
    "Hourse Mackerel": {
        "common_name": "Horse Mackerel",
        "scientific_name": "Trachurus trachurus",
        "taxonomy_species_id": None,
    },
    "Red Mullet": {
        "common_name": "Red Mullet",
        "scientific_name": "Mullus barbatus",
        "taxonomy_species_id": None,
    },
    "Red Sea Bream": {
        "common_name": "Red Sea Bream",
        "scientific_name": "Pagrus major",
        "taxonomy_species_id": None,
    },
    "Sea Bass": {
        "common_name": "European Seabass",
        "scientific_name": "Dicentrarchus labrax",
        "taxonomy_species_id": "european-seabass",
    },
    "Shrimp": {
        "common_name": "Shrimp",
        "scientific_name": "Caridea",
        "taxonomy_species_id": None,
    },
    "Striped Red Mullet": {
        "common_name": "Striped Red Mullet",
        "scientific_name": "Mullus surmuletus",
        "taxonomy_species_id": None,
    },
    "Trout": {
        "common_name": "Trout",
        "scientific_name": None,
        "taxonomy_species_id": None,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--mode", choices=["manifest-only", "symlink", "copy"], default="manifest-only")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--val-fraction", type=float, default=0.15)
    parser.add_argument("--test-fraction", type=float, default=0.15)
    parser.add_argument(
        "--include-shrimp-as-negative",
        action="store_true",
        help="Include shrimp images as no-fish negatives. Disabled by default to keep the fish detector clean.",
    )
    return parser.parse_args()


def find_fish_dataset_root(path: Path) -> Path:
    candidates = [
        path,
        path / "Fish_Dataset",
        path / "Fish_Dataset" / "Fish_Dataset",
    ]
    for candidate in candidates:
        if candidate.exists() and any((candidate / name).is_dir() for name in SOURCE_CLASS_METADATA):
            return candidate
    raise SystemExit(f"Could not find Fish_Dataset class folders under {path}")


def image_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(
        item
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )


def mask_bbox(mask_path: Path) -> list[float] | None:
    with Image.open(mask_path) as image:
        mask = np.asarray(image.convert("L"))
    ys, xs = np.where(mask > 0)
    if len(xs) == 0 or len(ys) == 0:
        return None
    x1 = float(xs.min())
    y1 = float(ys.min())
    x2 = float(xs.max() + 1)
    y2 = float(ys.max() + 1)
    return [x1, y1, x2 - x1, y2 - y1]


def materialize(source: Path, destination: Path, mode: str) -> None:
    if mode == "manifest-only":
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        return
    if mode == "copy":
        shutil.copy2(source, destination)
    else:
        destination.symlink_to(source.resolve())


def assign_splits(rows: list[dict], seed: int, val_fraction: float, test_fraction: float) -> dict[str, str]:
    if val_fraction < 0 or test_fraction < 0 or val_fraction + test_fraction >= 1:
        raise SystemExit("--val-fraction and --test-fraction must be non-negative and sum to less than 1")

    rng = random.Random(seed)
    by_class: dict[str, list[dict]] = {}
    for row in rows:
        by_class.setdefault(str(row["source_class"]), []).append(row)

    assignments = {}
    for class_rows in by_class.values():
        shuffled = list(class_rows)
        rng.shuffle(shuffled)
        total = len(shuffled)
        test_count = round(total * test_fraction)
        val_count = round(total * val_fraction)
        for index, row in enumerate(shuffled):
            if index < test_count:
                split = "test"
            elif index < test_count + val_count:
                split = "val"
            else:
                split = "train"
            assignments[row["image_id"]] = split
    return assignments


def build_rows(dataset_root: Path, include_shrimp_as_negative: bool) -> tuple[list[dict], Counter]:
    rows = []
    skipped: Counter[str] = Counter()

    for class_name, metadata in sorted(SOURCE_CLASS_METADATA.items()):
        class_root = dataset_root / class_name
        image_root = class_root / class_name
        mask_root = class_root / f"{class_name} GT"
        if not image_root.exists() or not mask_root.exists():
            skipped["missing_class_folder"] += 1
            continue

        for image_path in image_files(image_root):
            mask_path = mask_root / image_path.name
            if not mask_path.exists():
                skipped["missing_mask"] += 1
                continue

            image_id = f"large_scale_fish_{class_name.lower().replace(' ', '_').replace('-', '_')}_{image_path.stem}"
            annotations = []
            labels = []
            if class_name == "Shrimp":
                if not include_shrimp_as_negative:
                    skipped["shrimp"] += 1
                    continue
            else:
                bbox = mask_bbox(mask_path)
                if bbox is None:
                    skipped["empty_mask"] += 1
                    continue
                annotations = [{"label": "fish", "bbox_xywh": bbox}]
                labels = ["fish"]

            rows.append(
                {
                    "image_id": image_id,
                    "image": str(Path("images") / class_name / image_path.name),
                    "mask": str(Path("masks") / class_name / mask_path.name),
                    "task": "detection",
                    "labels": labels,
                    "annotations": annotations,
                    "source": "kaggle-large-scale-fish-dataset",
                    "license": "cc-by-4.0",
                    "source_class": class_name,
                    "source_common_name": metadata["common_name"],
                    "source_species_name": metadata["scientific_name"],
                    "species_id": metadata["taxonomy_species_id"],
                    "source_path": str(image_path),
                    "mask_path": str(mask_path),
                    "scenario_tags": ["public-seed", "controlled-market", "segmentation-mask"],
                }
            )

    return rows, skipped


def main() -> int:
    args = parse_args()
    dataset_root = find_fish_dataset_root(args.dataset_root)
    rows, skipped = build_rows(dataset_root, args.include_shrimp_as_negative)
    assignments = assign_splits(rows, args.seed, args.val_fraction, args.test_fraction)

    args.output_root.mkdir(parents=True, exist_ok=True)
    split_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    box_counts: Counter[str] = Counter()

    manifest_path = args.output_root / "manifest.jsonl"
    classification_manifest_path = args.output_root / "classification_mapped.manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as manifest_handle, classification_manifest_path.open(
        "w",
        encoding="utf-8",
    ) as classification_handle:
        for row in rows:
            split = assignments[row["image_id"]]
            image_path = Path(row["source_path"])
            mask_path = Path(row["mask_path"])
            materialize(image_path, args.output_root / row["image"], args.mode)
            materialize(mask_path, args.output_root / row["mask"], args.mode)

            output_row = {**row, "split": split}
            manifest_handle.write(json.dumps(output_row, sort_keys=True))
            manifest_handle.write("\n")

            if output_row.get("species_id"):
                classification_handle.write(json.dumps(output_row, sort_keys=True))
                classification_handle.write("\n")

            split_counts[split] += 1
            class_counts[row["source_class"]] += 1
            box_counts[split] += len(row["annotations"])

    report = {
        "dataset_root": str(dataset_root),
        "output_root": str(args.output_root),
        "mode": args.mode,
        "manifest": str(manifest_path),
        "classification_mapped_manifest": str(classification_manifest_path),
        "manifest_rows": len(rows),
        "mapped_classification_rows": sum(1 for row in rows if row.get("species_id")),
        "class_counts": dict(sorted(class_counts.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "box_counts": dict(sorted(box_counts.items())),
        "skipped": dict(sorted(skipped.items())),
        "seed": args.seed,
        "license": "cc-by-4.0",
    }
    (args.output_root / "source_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
