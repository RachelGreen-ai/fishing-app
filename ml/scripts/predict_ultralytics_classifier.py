#!/usr/bin/env python3
"""Run an Ultralytics classification model on a manifest and write prediction JSONL."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_path", type=Path)
    parser.add_argument("manifest_jsonl", type=Path)
    parser.add_argument("image_root", type=Path)
    parser.add_argument("output_predictions_jsonl", type=Path)
    parser.add_argument("--top-k", type=int, default=5)
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
            image_id = row["image_id"]
            image_path = args.image_root / row["image"]
            start = time.perf_counter()
            result = model(str(image_path), verbose=False)[0]
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            probabilities = result.probs.data.detach().cpu()
            scores, indices = torch.topk(probabilities, k=min(args.top_k, probabilities.numel()))
            predictions = [
                {
                    "label": names[int(index)],
                    "score": float(score),
                }
                for score, index in zip(scores, indices, strict=True)
            ]
            handle.write(
                json.dumps(
                    {
                        "image_id": image_id,
                        "predictions": predictions,
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
