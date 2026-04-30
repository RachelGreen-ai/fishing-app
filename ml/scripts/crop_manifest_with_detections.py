#!/usr/bin/env python3
"""Create a cropped classification manifest from detector predictions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_jsonl", type=Path)
    parser.add_argument("image_root", type=Path)
    parser.add_argument("detections_jsonl", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--min-score", type=float, default=0.25)
    parser.add_argument("--padding", type=float, default=0.08)
    parser.add_argument("--fallback", choices=["full-image", "skip"], default="full-image")
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


def best_fish_detection(prediction: dict, min_score: float) -> dict | None:
    detections = [
        detection
        for detection in prediction.get("detections") or []
        if str(detection.get("label", "fish")) == "fish"
        and float(detection.get("score", 0.0)) >= min_score
    ]
    if not detections:
        return None
    return max(detections, key=lambda detection: float(detection.get("score", 0.0)))


def padded_box(box: list[float], width: int, height: int, padding: float) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = [float(value) for value in box]
    box_width = max(1.0, x2 - x1)
    box_height = max(1.0, y2 - y1)
    pad_x = box_width * padding
    pad_y = box_height * padding
    left = int(max(0.0, x1 - pad_x))
    top = int(max(0.0, y1 - pad_y))
    right = int(min(float(width), x2 + pad_x))
    bottom = int(min(float(height), y2 + pad_y))
    return left, top, right, bottom


def output_image_path(row: dict, detected: bool, original_suffix: str) -> Path:
    split = str(row.get("split", "unsplit"))
    species_id = str(row.get("species_id", "unknown"))
    suffix = original_suffix.lower() if original_suffix else ".jpg"
    return Path(split) / species_id / f"{row['image_id']}_{'crop' if detected else 'full'}{suffix}"


def main() -> int:
    args = parse_args()
    manifest_rows = load_jsonl(args.manifest_jsonl)
    predictions_by_id = {row["image_id"]: row for row in load_jsonl(args.detections_jsonl)}

    args.output_root.mkdir(parents=True, exist_ok=True)
    cropped_rows = []
    detected_count = 0
    fallback_count = 0
    skipped_count = 0

    for row in manifest_rows:
        prediction = predictions_by_id.get(row["image_id"])
        if prediction is None:
            raise SystemExit(f"Missing detection prediction for {row['image_id']}")
        image_path = args.image_root / row["image"]
        if not image_path.exists() and row.get("source_path"):
            image_path = Path(row["source_path"])
        if not image_path.exists():
            raise SystemExit(f"Image not found for {row['image_id']}: {image_path}")

        detection = best_fish_detection(prediction, args.min_score)
        if detection is None and args.fallback == "skip":
            skipped_count += 1
            continue

        with Image.open(image_path) as image:
            image = image.convert("RGB")
            width, height = image.size
            if detection is not None:
                crop_box = padded_box(detection["bbox_xyxy"], width, height, args.padding)
                output_image = image.crop(crop_box)
                detected = True
                detected_count += 1
            else:
                crop_box = [0, 0, width, height]
                output_image = image
                detected = False
                fallback_count += 1

            relative_output = output_image_path(row, detected, image_path.suffix)
            output_path = args.output_root / relative_output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_image.save(output_path, quality=95)

        cropped_rows.append(
            {
                **row,
                "image": str(relative_output),
                "original_image": row.get("image"),
                "detector_crop": {
                    "detected": detected,
                    "bbox_xyxy": crop_box,
                    "score": float(detection["score"]) if detection is not None else None,
                    "padding": args.padding,
                },
            }
        )

    manifest_path = args.output_root / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as handle:
        for row in cropped_rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")

    report = {
        "manifest": str(manifest_path),
        "input_rows": len(manifest_rows),
        "output_rows": len(cropped_rows),
        "detected_crops": detected_count,
        "fallback_full_images": fallback_count,
        "skipped_rows": skipped_count,
        "min_score": args.min_score,
        "padding": args.padding,
        "fallback": args.fallback,
    }
    (args.output_root / "crop_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
