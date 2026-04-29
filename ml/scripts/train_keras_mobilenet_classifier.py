#!/usr/bin/env python3
"""Train a Keras MobileNet-family fish classifier from a split directory."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import tensorflow as tf


ARCHITECTURES = {
    "mobilenet_v2",
    "mobilenet_v3_small",
    "mobilenet_v3_large",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--architecture", choices=sorted(ARCHITECTURES), default="mobilenet_v3_small")
    parser.add_argument("--weights", choices=["imagenet", "none"], default="imagenet")
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--fine-tune-epochs", type=int, default=10)
    parser.add_argument("--fine-tune-layers", type=int, default=40)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--fine-tune-learning-rate", type=float, default=1e-5)
    parser.add_argument("--dropout", type=float, default=0.25)
    parser.add_argument("--label-smoothing", type=float, default=0.0)
    parser.add_argument("--class-weight-json", type=Path)
    parser.add_argument("--class-weight-region")
    parser.add_argument(
        "--class-weight-strength",
        type=float,
        default=1.0,
        help="Exponent applied to prior/equal class weights; use 0.5 for a gentler prior.",
    )
    parser.add_argument("--seed", type=int, default=20260428)
    parser.add_argument("--export-coreml", action="store_true")
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    tf.keras.utils.set_random_seed(seed)


def class_names(train_root: Path) -> list[str]:
    names = sorted(path.name for path in train_root.iterdir() if path.is_dir())
    if not names:
        raise SystemExit(f"No class directories found in {train_root}")
    return names


def make_dataset(root: Path, labels: list[str], image_size: int, batch_size: int, shuffle: bool, seed: int):
    return tf.keras.utils.image_dataset_from_directory(
        root,
        labels="inferred",
        label_mode="categorical",
        class_names=labels,
        image_size=(image_size, image_size),
        batch_size=batch_size,
        shuffle=shuffle,
        seed=seed,
    ).prefetch(tf.data.AUTOTUNE)


def backbone(name: str, image_size: int, weights: str | None) -> tf.keras.Model:
    input_shape = (image_size, image_size, 3)
    if name == "mobilenet_v2":
        return tf.keras.applications.MobileNetV2(
            input_shape=input_shape,
            include_top=False,
            weights=weights,
            pooling="avg",
        )
    if name == "mobilenet_v3_large":
        return tf.keras.applications.MobileNetV3Large(
            input_shape=input_shape,
            include_top=False,
            weights=weights,
            pooling="avg",
            include_preprocessing=True,
        )
    return tf.keras.applications.MobileNetV3Small(
        input_shape=input_shape,
        include_top=False,
        weights=weights,
        pooling="avg",
        include_preprocessing=True,
    )


def build_model(args: argparse.Namespace, labels: list[str]) -> tf.keras.Model:
    inputs = tf.keras.Input(shape=(args.image_size, args.image_size, 3), name="image")
    x = tf.keras.layers.RandomFlip("horizontal")(inputs)
    x = tf.keras.layers.RandomRotation(0.04)(x)
    x = tf.keras.layers.RandomZoom(0.08)(x)
    x = tf.keras.layers.RandomContrast(0.15)(x)

    if args.architecture == "mobilenet_v2":
        x = tf.keras.applications.mobilenet_v2.preprocess_input(x)

    weights = None if args.weights == "none" else args.weights
    base = backbone(args.architecture, args.image_size, weights)
    base.trainable = weights is None
    x = base(x, training=False)
    x = tf.keras.layers.Dropout(args.dropout)(x)
    outputs = tf.keras.layers.Dense(len(labels), activation="softmax", name="species")(x)
    return tf.keras.Model(inputs, outputs, name=f"fish_{args.architecture}")


def load_class_weights(args: argparse.Namespace, labels: list[str]) -> dict[int, float] | None:
    if not args.class_weight_json:
        return None
    if not args.class_weight_region:
        raise SystemExit("--class-weight-region is required with --class-weight-json")

    prior = json.loads(args.class_weight_json.read_text(encoding="utf-8"))
    region = prior.get("regions", {}).get(args.class_weight_region)
    if not region:
        available = ", ".join(sorted(prior.get("regions", {}))) or "<none>"
        raise SystemExit(f"Region {args.class_weight_region!r} not found. Available: {available}")

    species_weights = region.get("species_weights") or {}
    missing = [label for label in labels if label not in species_weights]
    if missing:
        raise SystemExit(f"Class-weight prior missing labels: {missing}")

    equal_weight = 1.0 / len(labels)
    raw_weights = [
        (float(species_weights[label]) / equal_weight) ** args.class_weight_strength
        for label in labels
    ]
    mean_weight = float(np.mean(raw_weights))
    return {
        index: float(weight / mean_weight)
        for index, weight in enumerate(raw_weights)
    }


def compile_model(model: tf.keras.Model, learning_rate: float, label_smoothing: float) -> None:
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss=tf.keras.losses.CategoricalCrossentropy(label_smoothing=label_smoothing),
        metrics=[
            "accuracy",
            tf.keras.metrics.TopKCategoricalAccuracy(k=3, name="top3_accuracy"),
        ],
    )


def unfreeze_tail(model: tf.keras.Model, architecture: str, fine_tune_layers: int) -> None:
    base = next((layer for layer in model.layers if architecture in layer.name.lower()), None)
    if base is None:
        # Keras may name MobileNetV3Small "MobilenetV3small"; fall back to the nested model.
        base = next((layer for layer in model.layers if isinstance(layer, tf.keras.Model)), None)
    if base is None:
        raise SystemExit("Could not find MobileNet backbone to fine-tune")

    base.trainable = True
    trainable_from = max(0, len(base.layers) - fine_tune_layers)
    for index, layer in enumerate(base.layers):
        layer.trainable = index >= trainable_from and not isinstance(layer, tf.keras.layers.BatchNormalization)


def export_coreml(model: tf.keras.Model, labels: list[str], output_path: Path, image_size: int) -> None:
    try:
        import coremltools as ct
    except ImportError as exc:
        raise SystemExit("coremltools is required for --export-coreml") from exc

    classifier_config = ct.ClassifierConfig(labels)
    mlmodel = ct.convert(
        model,
        inputs=[
            ct.ImageType(
                name="image",
                shape=(1, image_size, image_size, 3),
                scale=1.0,
                bias=[0.0, 0.0, 0.0],
                color_layout=ct.colorlayout.RGB,
            )
        ],
        classifier_config=classifier_config,
        minimum_deployment_target=ct.target.iOS17,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mlmodel.save(str(output_path))


def main() -> int:
    args = parse_args()
    set_seed(args.seed)

    train_root = args.dataset_root / "train"
    validation_root = args.dataset_root / "validation"
    test_root = args.dataset_root / "test"
    labels = class_names(train_root)

    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")

    train_ds = make_dataset(train_root, labels, args.image_size, args.batch_size, True, args.seed)
    validation_ds = make_dataset(validation_root, labels, args.image_size, args.batch_size, False, args.seed)
    test_ds = make_dataset(test_root, labels, args.image_size, args.batch_size, False, args.seed)

    model = build_model(args, labels)
    class_weights = load_class_weights(args, labels)
    compile_model(model, args.learning_rate, args.label_smoothing)

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=5,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(args.output_root / "best.keras"),
            monitor="val_accuracy",
            save_best_only=True,
        ),
    ]

    history = model.fit(
        train_ds,
        validation_data=validation_ds,
        epochs=args.epochs,
        callbacks=callbacks,
        class_weight=class_weights,
        verbose=2,
    )

    if args.fine_tune_epochs > 0:
        unfreeze_tail(model, args.architecture, args.fine_tune_layers)
        compile_model(model, args.fine_tune_learning_rate, args.label_smoothing)
        fine_history = model.fit(
            train_ds,
            validation_data=validation_ds,
            epochs=args.fine_tune_epochs,
            callbacks=callbacks,
            class_weight=class_weights,
            verbose=2,
        )
        for key, values in fine_history.history.items():
            history.history.setdefault(f"fine_tune_{key}", values)

    test_metrics = model.evaluate(test_ds, verbose=0, return_dict=True)
    model.save(str(args.output_root / "final.keras"))

    report = {
        "architecture": args.architecture,
        "dataset_root": str(args.dataset_root),
        "labels": labels,
        "image_size": args.image_size,
        "weights": args.weights,
        "batch_size": args.batch_size,
        "epochs": args.epochs,
        "fine_tune_epochs": args.fine_tune_epochs,
        "fine_tune_layers": args.fine_tune_layers,
        "label_smoothing": args.label_smoothing,
        "class_weight_json": str(args.class_weight_json) if args.class_weight_json else None,
        "class_weight_region": args.class_weight_region,
        "class_weight_strength": args.class_weight_strength,
        "class_weights": class_weights,
        "test_metrics": {key: float(value) for key, value in test_metrics.items()},
        "history": {
            key: [float(value) for value in values]
            for key, values in history.history.items()
        },
    }
    (args.output_root / "training_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    if args.export_coreml:
        export_coreml(
            model,
            labels,
            args.output_root / "FishSpeciesClassifier.mlpackage",
            args.image_size,
        )

    print(json.dumps(report["test_metrics"], indent=2, sort_keys=True))
    print(f"wrote_model={args.output_root / 'final.keras'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
