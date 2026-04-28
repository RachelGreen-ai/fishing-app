#!/usr/bin/env python3
"""Evaluate fish length and weight estimates against measured ground truth."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_jsonl", type=Path)
    parser.add_argument("predictions_jsonl", type=Path)
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


def absolute_percentage_error(actual: float, estimated: float) -> float:
    if actual == 0:
        return 0.0
    return abs(estimated - actual) / actual


def within(errors: list[float], threshold: float) -> float:
    if not errors:
        return 0.0
    return sum(1 for error in errors if error <= threshold) / len(errors)


def main() -> int:
    args = parse_args()
    manifest_rows = load_jsonl(args.manifest_jsonl)
    prediction_rows = {row["image_id"]: row for row in load_jsonl(args.predictions_jsonl)}

    length_errors_cm = []
    length_apes = []
    weight_errors_g = []
    weight_apes = []
    missing_predictions = []

    for truth in manifest_rows:
        image_id = truth["image_id"]
        prediction = prediction_rows.get(image_id)
        if prediction is None:
            missing_predictions.append(image_id)
            continue

        if "measured_total_length_cm" in truth and "estimated_total_length_cm" in prediction:
            actual_length = float(truth["measured_total_length_cm"])
            estimated_length = float(prediction["estimated_total_length_cm"])
            length_errors_cm.append(abs(estimated_length - actual_length))
            length_apes.append(absolute_percentage_error(actual_length, estimated_length))

        if "measured_weight_g" in truth and "estimated_weight_g" in prediction:
            actual_weight = float(truth["measured_weight_g"])
            estimated_weight = float(prediction["estimated_weight_g"])
            weight_errors_g.append(abs(estimated_weight - actual_weight))
            weight_apes.append(absolute_percentage_error(actual_weight, estimated_weight))

    if missing_predictions:
        raise SystemExit(f"Missing predictions for {len(missing_predictions)} images: {missing_predictions[:5]}")

    report = {
        "count": len(manifest_rows),
        "length": {
            "count": len(length_errors_cm),
            "mae_cm": round(mean(length_errors_cm), 3) if length_errors_cm else None,
            "mape": round(mean(length_apes), 4) if length_apes else None,
            "within_1cm": round(within(length_errors_cm, 1.0), 4),
            "within_2cm": round(within(length_errors_cm, 2.0), 4),
            "within_5cm": round(within(length_errors_cm, 5.0), 4),
        },
        "weight": {
            "count": len(weight_errors_g),
            "mae_g": round(mean(weight_errors_g), 3) if weight_errors_g else None,
            "mape": round(mean(weight_apes), 4) if weight_apes else None,
        },
    }

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
