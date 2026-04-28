#!/usr/bin/env python3
"""Prepare a detection manifest for NOAA Labeled Fishes in the Wild."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lfiw_root", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--mode", choices=["manifest-only", "copy"], default="manifest-only")
    return parser.parse_args()


def read_marks(path: Path) -> dict[str, list[dict]]:
    marks: dict[str, list[dict]] = {}
    if not path.exists():
        return marks

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            parts = line.strip().split()
            if not parts:
                continue
            if len(parts) < 6:
                raise SystemExit(f"{path}:{line_number}: expected filename count x y w h")
            image_name = parts[0]
            try:
                x, y, width, height = map(float, parts[2:6])
            except ValueError as exc:
                raise SystemExit(f"{path}:{line_number}: invalid bbox values") from exc
            marks.setdefault(image_name, []).append(
                {
                    "label": "fish",
                    "bbox_xywh": [x, y, width, height],
                }
            )
    return marks


def image_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(
        item
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )


def materialize(source: Path, destination: Path, mode: str) -> None:
    if mode == "manifest-only":
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copy2(source, destination)


def main() -> int:
    args = parse_args()
    if not args.lfiw_root.exists():
        raise SystemExit(f"NOAA LFIW root does not exist: {args.lfiw_root}")

    positive_root = args.lfiw_root / "Training_and_validation" / "Positive_fish"
    negative_root = args.lfiw_root / "Negatives (seabed)"
    test_root = args.lfiw_root / "Test"
    positive_marks = read_marks(positive_root / "Positive_fish_(ALL)-MARKS_DATA.dat")
    test_marks = read_marks(test_root / "Test_ROV_video_h264_full_marks.dat")

    rows = []
    positive_count = 0
    negative_count = 0
    bbox_count = 0

    for source_path in image_files(positive_root):
        image_id = f"noaa_lfiw_train_{source_path.stem}"
        destination = args.output_root / "images" / "train_positive" / source_path.name
        materialize(source_path, destination, args.mode)
        boxes = positive_marks.get(source_path.name, [])
        bbox_count += len(boxes)
        positive_count += 1
        rows.append(
            {
                "image_id": image_id,
                "image": str(destination.relative_to(args.output_root)),
                "task": "detection",
                "split": "train_validation",
                "labels": ["fish"] if boxes else [],
                "annotations": boxes,
                "source": "noaa-labeled-fishes-in-the-wild",
                "license": "public-domain-us-government",
                "source_path": str(source_path),
            }
        )

    for source_path in image_files(negative_root):
        image_id = f"noaa_lfiw_negative_{source_path.stem}"
        destination = args.output_root / "images" / "negative" / source_path.name
        materialize(source_path, destination, args.mode)
        negative_count += 1
        rows.append(
            {
                "image_id": image_id,
                "image": str(destination.relative_to(args.output_root)),
                "task": "detection",
                "split": "train_validation_negative",
                "labels": [],
                "annotations": [],
                "source": "noaa-labeled-fishes-in-the-wild",
                "license": "public-domain-us-government",
                "source_path": str(source_path),
            }
        )

    args.output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_root / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")

    report = {
        "output_root": str(args.output_root),
        "mode": args.mode,
        "train_positive_images": positive_count,
        "negative_images": negative_count,
        "train_positive_boxes": bbox_count,
        "test_video_mark_rows": sum(len(boxes) for boxes in test_marks.values()),
        "manifest_rows": len(rows),
    }
    (args.output_root / "source_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
