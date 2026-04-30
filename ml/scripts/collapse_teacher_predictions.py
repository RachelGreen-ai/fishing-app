#!/usr/bin/env python3
"""Collapse external teacher predictions into app taxonomy predictions."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("teacher_predictions_jsonl", type=Path)
    parser.add_argument("teacher_label_map_json", type=Path)
    parser.add_argument("output_predictions_jsonl", type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--include-teacher-details", action="store_true")
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


def teacher_lookup(label_map: dict) -> dict[str, dict]:
    lookup = {}
    for mapped in label_map.get("mapped_teacher_labels", {}).values():
        lookup[str(mapped["teacher_label"])] = mapped
        lookup[str(mapped["teacher_id"])] = mapped
    return lookup


def prediction_label(prediction: dict) -> str:
    return str(
        prediction.get("label")
        or prediction.get("teacher_label")
        or prediction.get("class_name")
        or prediction.get("id")
        or prediction.get("class_id")
        or ""
    )


def prediction_score(prediction: dict) -> float:
    return float(prediction.get("score", prediction.get("confidence", prediction.get("probability", 0.0))))


def main() -> int:
    args = parse_args()
    label_map = load_json(args.teacher_label_map_json)
    lookup = teacher_lookup(label_map)
    rows = load_jsonl(args.teacher_predictions_jsonl)

    args.output_predictions_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_predictions_jsonl.open("w", encoding="utf-8") as handle:
        for row in rows:
            app_scores: dict[str, float] = defaultdict(float)
            teacher_details = []

            for prediction in row.get("predictions", []):
                label = prediction_label(prediction)
                mapped = lookup.get(label)
                if not mapped:
                    continue

                score = prediction_score(prediction)
                app_scores[mapped["app_id"]] += score
                teacher_details.append(
                    {
                        "teacher_label": mapped["teacher_label"],
                        "teacher_id": mapped["teacher_id"],
                        "app_id": mapped["app_id"],
                        "score": score,
                    }
                )

            ranked = sorted(app_scores.items(), key=lambda item: item[1], reverse=True)[: args.top_k]
            output_row = {
                "image_id": row["image_id"],
                "predictions": [
                    {
                        "label": app_id,
                        "score": score,
                    }
                    for app_id, score in ranked
                ],
            }
            if "latency_ms" in row:
                output_row["latency_ms"] = row["latency_ms"]
            if not ranked:
                output_row["abstained"] = True
            if args.include_teacher_details:
                output_row["teacher_details"] = teacher_details

            handle.write(json.dumps(output_row, sort_keys=True))
            handle.write("\n")

    print(f"wrote_predictions={args.output_predictions_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
