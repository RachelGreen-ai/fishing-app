#!/usr/bin/env python3
"""Convert a generic fish detection manifest into an Ultralytics YOLO dataset."""

from __future__ import annotations

import argparse
import json
import random
import shutil
from collections import Counter
from pathlib import Path

from PIL import Image


CLASS_NAMES = ["fish"]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_jsonl", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument(
        "--image-root",
        type=Path,
        help="Root for manifest image paths. Defaults to the manifest parent directory.",
    )
    parser.add_argument("--mode", choices=["symlink", "copy"], default="symlink")
    parser.add_argument("--val-fraction", type=float, default=0.15)
    parser.add_argument("--test-fraction", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--include-unannotated-positive",
        action="store_true",
        help=(
            "Include positive-source rows with no boxes as negatives. Disabled by default "
            "because missing boxes can teach the detector that visible fish are background."
        ),
    )
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


def resolve_image_path(row: dict, image_root: Path) -> Path:
    image_path = image_root / row["image"]
    if image_path.exists():
        return image_path

    source_path = Path(str(row.get("source_path", "")))
    if source_path.exists():
        return source_path

    raise SystemExit(f"Image not found for {row.get('image_id', '<unknown>')}: {image_path}")


def is_positive_source(row: dict) -> bool:
    split = str(row.get("split", ""))
    image = str(row.get("image", ""))
    return "positive" in split or "train_positive" in image


def materialize(source: Path, destination: Path, mode: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        return
    if mode == "copy":
        shutil.copy2(source, destination)
    else:
        destination.symlink_to(source.resolve())


def yolo_lines(row: dict, width: int, height: int) -> list[str]:
    lines = []
    for annotation in row.get("annotations") or []:
        if annotation.get("label") != "fish":
            continue
        x, y, box_width, box_height = [float(value) for value in annotation["bbox_xywh"]]
        x1 = max(0.0, min(float(width), x))
        y1 = max(0.0, min(float(height), y))
        x2 = max(0.0, min(float(width), x + box_width))
        y2 = max(0.0, min(float(height), y + box_height))
        clipped_width = x2 - x1
        clipped_height = y2 - y1
        if clipped_width <= 1 or clipped_height <= 1:
            continue

        center_x = (x1 + clipped_width / 2.0) / width
        center_y = (y1 + clipped_height / 2.0) / height
        normalized_width = clipped_width / width
        normalized_height = clipped_height / height
        lines.append(
            f"0 {center_x:.8f} {center_y:.8f} {normalized_width:.8f} {normalized_height:.8f}"
        )
    return lines


def assign_splits(rows: list[dict], val_fraction: float, test_fraction: float, seed: int) -> dict[str, str]:
    if val_fraction < 0 or test_fraction < 0 or val_fraction + test_fraction >= 1:
        raise SystemExit("--val-fraction and --test-fraction must be non-negative and sum to less than 1")

    rng = random.Random(seed)
    positives = [row for row in rows if row.get("annotations")]
    negatives = [row for row in rows if not row.get("annotations")]
    assignments: dict[str, str] = {}

    for group in (positives, negatives):
        shuffled = list(group)
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


def image_destination(row: dict, source_path: Path, split: str) -> Path:
    suffix = source_path.suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        suffix = ".jpg"
    return Path("images") / split / f"{row['image_id']}{suffix}"


def main() -> int:
    args = parse_args()
    image_root = args.image_root or args.manifest_jsonl.parent
    rows = load_jsonl(args.manifest_jsonl)
    usable_rows = []
    skipped_unannotated_positive = 0

    for row in rows:
        if not row.get("annotations") and is_positive_source(row) and not args.include_unannotated_positive:
            skipped_unannotated_positive += 1
            continue
        usable_rows.append(row)

    assignments = assign_splits(usable_rows, args.val_fraction, args.test_fraction, args.seed)
    split_counts: Counter[str] = Counter()
    box_counts: Counter[str] = Counter()
    manifest_rows = []

    args.output_root.mkdir(parents=True, exist_ok=True)
    for row in usable_rows:
        split = assignments[row["image_id"]]
        source_path = resolve_image_path(row, image_root)
        with Image.open(source_path) as image:
            width, height = image.size
        relative_image = image_destination(row, source_path, split)
        destination_image = args.output_root / relative_image
        materialize(source_path, destination_image, args.mode)

        label_path = args.output_root / "labels" / split / f"{row['image_id']}.txt"
        label_path.parent.mkdir(parents=True, exist_ok=True)
        label_lines = yolo_lines(row, width, height)
        label_path.write_text("\n".join(label_lines) + ("\n" if label_lines else ""), encoding="utf-8")

        split_counts[split] += 1
        box_counts[split] += len(label_lines)
        manifest_rows.append(
            {
                **row,
                "split": split,
                "image": str(relative_image),
                "source_image": row.get("image"),
                "source_path": str(source_path),
            }
        )

    dataset_yaml = args.output_root / "dataset.yaml"
    dataset_yaml.write_text(
        "\n".join(
            [
                f"path: {args.output_root.resolve()}",
                "train: images/train",
                "val: images/val",
                "test: images/test",
                "names:",
                "  0: fish",
                "",
            ]
        ),
        encoding="utf-8",
    )

    split_manifest = args.output_root / "manifest.jsonl"
    with split_manifest.open("w", encoding="utf-8") as handle:
        for row in manifest_rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")

    report = {
        "dataset_yaml": str(dataset_yaml),
        "manifest_rows": len(manifest_rows),
        "skipped_unannotated_positive_rows": skipped_unannotated_positive,
        "split_counts": dict(sorted(split_counts.items())),
        "box_counts": dict(sorted(box_counts.items())),
        "class_names": CLASS_NAMES,
        "mode": args.mode,
        "seed": args.seed,
    }
    (args.output_root / "source_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
