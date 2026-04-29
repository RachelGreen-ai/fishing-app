#!/usr/bin/env python3
"""Export a Keras fish classifier to a Core ML classifier package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import tensorflow as tf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_path", type=Path)
    parser.add_argument("labels_json", type=Path)
    parser.add_argument("output_mlpackage", type=Path)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--minimum-ios", choices=["16", "17"], default="17")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    labels = json.loads(args.labels_json.read_text(encoding="utf-8"))
    model = tf.keras.models.load_model(args.model_path)

    try:
        import coremltools as ct
    except ImportError as exc:
        raise SystemExit("coremltools is required for export") from exc

    target = ct.target.iOS17 if args.minimum_ios == "17" else ct.target.iOS16
    classifier_config = ct.ClassifierConfig(labels)
    mlmodel = ct.convert(
        model,
        inputs=[
            ct.ImageType(
                name="image",
                shape=(1, args.image_size, args.image_size, 3),
                scale=1.0,
                bias=[0.0, 0.0, 0.0],
                color_layout=ct.colorlayout.RGB,
            )
        ],
        classifier_config=classifier_config,
        minimum_deployment_target=target,
    )

    args.output_mlpackage.parent.mkdir(parents=True, exist_ok=True)
    mlmodel.save(str(args.output_mlpackage))
    print(f"wrote_coreml={args.output_mlpackage}")
    print(f"labels={','.join(labels)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
