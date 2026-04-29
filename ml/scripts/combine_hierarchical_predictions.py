#!/usr/bin/env python3
"""Combine a general classifier with a specialist classifier prediction JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("general_predictions_jsonl", type=Path)
    parser.add_argument("specialist_predictions_jsonl", type=Path)
    parser.add_argument("output_predictions_jsonl", type=Path)
    parser.add_argument(
        "--specialist-label",
        action="append",
        required=True,
        help="Label owned by the specialist. Repeat for multiple labels.",
    )
    parser.add_argument(
        "--trigger",
        choices=["top1", "top3-any", "top3-majority"],
        default="top1",
        help="When to replace the general prediction with the specialist prediction.",
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


def top_labels(row: dict) -> list[str]:
    return [
        str(prediction.get("label"))
        for prediction in row.get("predictions", [])
        if prediction.get("label")
    ]


def should_use_specialist(labels: list[str], specialist_labels: set[str], trigger: str) -> bool:
    if not labels:
        return False
    if trigger == "top1":
        return labels[0] in specialist_labels
    top3 = labels[:3]
    matches = sum(1 for label in top3 if label in specialist_labels)
    if trigger == "top3-any":
        return matches > 0
    return matches >= 2


def merged_predictions(general: dict, specialist: dict, specialist_labels: set[str]) -> list[dict]:
    output = []
    seen = set()
    for prediction in specialist.get("predictions", []):
        label = prediction.get("label")
        if label in specialist_labels and label not in seen:
            output.append(prediction)
            seen.add(label)

    for prediction in general.get("predictions", []):
        label = prediction.get("label")
        if label and label not in seen:
            output.append(prediction)
            seen.add(label)

    return output[:5]


def main() -> int:
    args = parse_args()
    specialist_labels = set(args.specialist_label)
    general_rows = load_jsonl(args.general_predictions_jsonl)
    specialist_by_image_id = {
        row["image_id"]: row
        for row in load_jsonl(args.specialist_predictions_jsonl)
    }

    args.output_predictions_jsonl.parent.mkdir(parents=True, exist_ok=True)
    replaced = 0
    missing_specialist = 0

    with args.output_predictions_jsonl.open("w", encoding="utf-8") as handle:
        for general in general_rows:
            image_id = general["image_id"]
            labels = top_labels(general)
            output = dict(general)
            if should_use_specialist(labels, specialist_labels, args.trigger):
                specialist = specialist_by_image_id.get(image_id)
                if specialist and specialist.get("predictions"):
                    specialist_predictions = merged_predictions(general, specialist, specialist_labels)
                    if specialist_predictions:
                        output["predictions"] = specialist_predictions
                        output["specialist_applied"] = True
                        output["general_predictions"] = general.get("predictions", [])
                        output["latency_ms"] = float(general.get("latency_ms", 0.0)) + float(
                            specialist.get("latency_ms", 0.0)
                        )
                        replaced += 1
                else:
                    missing_specialist += 1

            handle.write(json.dumps(output, sort_keys=True))
            handle.write("\n")

    print(
        json.dumps(
            {
                "output": str(args.output_predictions_jsonl),
                "trigger": args.trigger,
                "specialist_labels": sorted(specialist_labels),
                "replaced": replaced,
                "missing_specialist": missing_specialist,
                "total": len(general_rows),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
