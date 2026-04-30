#!/usr/bin/env python3
"""Run an Ultralytics fish detector on a manifest and write detection JSONL."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from PIL import Image
from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_path", type=Path)
    parser.add_argument("manifest_jsonl", type=Path)
    parser.add_argument("image_root", type=Path)
    parser.add_argument("output_predictions_jsonl", type=Path)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.7)
    parser.add_argument("--max-det", type=int, default=10)
    parser.add_argument("--device", default=None)
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


def normalize_names(names: dict | list) -> dict[int, str]:
    if isinstance(names, dict):
        return {int(index): str(label) for index, label in names.items()}
    return {index: str(label) for index, label in enumerate(names)}


def main() -> int:
    args = parse_args()
    rows = load_jsonl(args.manifest_jsonl)
    model = YOLO(str(args.model_path))
    names = normalize_names(model.names)

    args.output_predictions_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_predictions_jsonl.open("w", encoding="utf-8") as handle:
        for row in rows:
            image_path = args.image_root / row["image"]
            if not image_path.exists() and row.get("source_path"):
                image_path = Path(row["source_path"])
            if not image_path.exists():
                raise SystemExit(f"Image not found for {row['image_id']}: {image_path}")

            with Image.open(image_path) as image:
                width, height = image.size

            start = time.perf_counter()
            result = model(
                str(image_path),
                imgsz=args.imgsz,
                conf=args.conf,
                iou=args.iou,
                max_det=args.max_det,
                device=args.device,
                verbose=False,
            )[0]
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            detections = []
            boxes = result.boxes
            if boxes is not None:
                xyxy = boxes.xyxy.detach().cpu().tolist()
                confs = boxes.conf.detach().cpu().tolist()
                classes = boxes.cls.detach().cpu().tolist()
                for box, score, class_index in zip(xyxy, confs, classes, strict=True):
                    x1, y1, x2, y2 = [float(value) for value in box]
                    detections.append(
                        {
                            "label": names.get(int(class_index), str(int(class_index))),
                            "score": float(score),
                            "bbox_xyxy": [x1, y1, x2, y2],
                            "bbox_xywh": [x1, y1, x2 - x1, y2 - y1],
                        }
                    )

            handle.write(
                json.dumps(
                    {
                        "image_id": row["image_id"],
                        "image_width": width,
                        "image_height": height,
                        "detections": detections,
                        "latency_ms": elapsed_ms,
                    },
                    sort_keys=True,
                )
            )
            handle.write("\n")

    print(f"wrote_predictions={args.output_predictions_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
