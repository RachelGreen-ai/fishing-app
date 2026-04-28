#!/usr/bin/env python3
"""Validate the fish image dataset layout before model training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
SPLITS = ("train", "validation", "test")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument("labels_json", type=Path)
    parser.add_argument("--min-train", type=int, default=500)
    parser.add_argument("--min-validation", type=int, default=100)
    parser.add_argument("--min-test", type=int, default=100)
    return parser.parse_args()


def load_labels(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as handle:
        rows = json.load(handle)

    labels = [row["id"] for row in rows]
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    if duplicates:
        raise SystemExit(f"Duplicate label IDs: {', '.join(duplicates)}")

    return labels


def image_count(path: Path) -> int:
    if not path.exists():
        return 0

    return sum(1 for item in path.iterdir() if item.suffix.lower() in IMAGE_EXTENSIONS)


def main() -> int:
    args = parse_args()
    labels = load_labels(args.labels_json)
    minimums = {
        "train": args.min_train,
        "validation": args.min_validation,
        "test": args.min_test,
    }

    errors: list[str] = []
    for split in SPLITS:
        split_root = args.dataset_root / split
        if not split_root.exists():
            errors.append(f"Missing split directory: {split_root}")
            continue

        for label in labels:
            label_root = split_root / label
            count = image_count(label_root)
            if count < minimums[split]:
                errors.append(
                    f"{split}/{label} has {count} images; expected at least {minimums[split]}"
                )

    if errors:
        print("Dataset is not ready for training:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Dataset looks trainable for {len(labels)} labels at {args.dataset_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
