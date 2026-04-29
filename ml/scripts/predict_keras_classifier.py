#!/usr/bin/env python3
"""Run a Keras fish classifier on a manifest and write prediction JSONL."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import tensorflow as tf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_path", type=Path)
    parser.add_argument("labels_json", type=Path)
    parser.add_argument("manifest_jsonl", type=Path)
    parser.add_argument("image_root", type=Path)
    parser.add_argument("output_predictions_jsonl", type=Path)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--tta-horizontal-flip",
        action="store_true",
        help="Average predictions for the image and a horizontal flip.",
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


def load_image(path: Path, image_size: int) -> np.ndarray:
    image = tf.keras.utils.load_img(path, target_size=(image_size, image_size), interpolation="bilinear")
    array = tf.keras.utils.img_to_array(image)
    return np.expand_dims(array, axis=0)


def predict_probabilities(model: tf.keras.Model, image: np.ndarray, tta_horizontal_flip: bool) -> np.ndarray:
    if not tta_horizontal_flip:
        return model.predict(image, verbose=0)[0]

    flipped = image[:, :, ::-1, :]
    batch = np.concatenate([image, flipped], axis=0)
    return np.mean(model.predict(batch, verbose=0), axis=0)


def main() -> int:
    args = parse_args()
    labels = json.loads(args.labels_json.read_text(encoding="utf-8"))
    model = tf.keras.models.load_model(args.model_path)
    rows = load_jsonl(args.manifest_jsonl)

    args.output_predictions_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_predictions_jsonl.open("w", encoding="utf-8") as handle:
        for row in rows:
            image_id = row["image_id"]
            image_path = args.image_root / row["image"]
            image = load_image(image_path, args.image_size)
            start = time.perf_counter()
            probabilities = predict_probabilities(model, image, args.tta_horizontal_flip)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            top_indices = np.argsort(probabilities)[::-1][: args.top_k]
            predictions = [
                {
                    "label": labels[int(index)],
                    "score": float(probabilities[int(index)]),
                }
                for index in top_indices
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
