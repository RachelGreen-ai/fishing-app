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
    parser.add_argument("--full-fine-tune-epochs", type=int, default=0)
    parser.add_argument("--full-fine-tune-learning-rate", type=float, default=2e-6)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--fine-tune-learning-rate", type=float, default=1e-5)
    parser.add_argument("--lr-schedule", choices=["constant", "cosine"], default="constant")
    parser.add_argument("--optimizer", choices=["adam", "adamw"], default="adam")
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--dropout", type=float, default=0.25)
    parser.add_argument("--label-smoothing", type=float, default=0.0)
    parser.add_argument("--augmentation-strength", choices=["light", "medium", "strong"], default="medium")
    parser.add_argument("--mixup-alpha", type=float, default=0.0)
    parser.add_argument("--class-weight-json", type=Path)
    parser.add_argument("--class-weight-region")
    parser.add_argument(
        "--class-weight-strength",
        type=float,
        default=1.0,
        help="Exponent applied to prior/equal class weights; use 0.5 for a gentler prior.",
    )
    parser.add_argument("--seed", type=int, default=20260428)
    parser.add_argument("--monitor", default="val_accuracy")
    parser.add_argument("--early-stopping-patience", type=int, default=5)
    parser.add_argument("--fine-tune-batchnorm", action="store_true")
    parser.add_argument(
        "--initial-backbone-model",
        type=Path,
        help="Optional Keras model whose matching MobileNet backbone weights seed this run.",
    )
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
    )


def augmentation_layers(strength: str) -> list[tf.keras.layers.Layer]:
    if strength == "light":
        return [
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.03),
            tf.keras.layers.RandomZoom(0.06),
            tf.keras.layers.RandomContrast(0.10),
        ]

    if strength == "strong":
        return [
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.08),
            tf.keras.layers.RandomTranslation(0.08, 0.08),
            tf.keras.layers.RandomZoom((-0.18, 0.12)),
            tf.keras.layers.RandomContrast(0.25),
            tf.keras.layers.RandomBrightness(0.12),
        ]

    return [
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.04),
        tf.keras.layers.RandomTranslation(0.04, 0.04),
        tf.keras.layers.RandomZoom(0.08),
        tf.keras.layers.RandomContrast(0.15),
    ]


def apply_mixup(dataset: tf.data.Dataset, alpha: float) -> tf.data.Dataset:
    if alpha <= 0:
        return dataset

    def mix(images, labels):
        batch_size = tf.shape(images)[0]
        gamma_1 = tf.random.gamma([batch_size], alpha)
        gamma_2 = tf.random.gamma([batch_size], alpha)
        lam = gamma_1 / (gamma_1 + gamma_2)
        lam_x = tf.reshape(lam, [batch_size, 1, 1, 1])
        lam_y = tf.reshape(lam, [batch_size, 1])
        indices = tf.random.shuffle(tf.range(batch_size))
        mixed_images = images * lam_x + tf.gather(images, indices) * (1.0 - lam_x)
        mixed_labels = labels * lam_y + tf.gather(labels, indices) * (1.0 - lam_y)
        return mixed_images, mixed_labels

    return dataset.map(mix, num_parallel_calls=tf.data.AUTOTUNE)


def apply_sample_weights(dataset: tf.data.Dataset, class_weights: dict[int, float]) -> tf.data.Dataset:
    weight_vector = tf.constant(
        [float(class_weights[index]) for index in sorted(class_weights)],
        dtype=tf.float32,
    )

    def add_weights(images, labels):
        sample_weights = tf.reduce_sum(labels * weight_vector, axis=-1)
        return images, labels, sample_weights

    return dataset.map(add_weights, num_parallel_calls=tf.data.AUTOTUNE)


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
    x = inputs
    for layer in augmentation_layers(args.augmentation_strength):
        x = layer(x)

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


def learning_rate(
    initial_learning_rate: float,
    schedule: str,
    epochs: int,
    steps_per_epoch: int,
):
    if schedule == "constant" or epochs <= 0:
        return initial_learning_rate
    return tf.keras.optimizers.schedules.CosineDecay(
        initial_learning_rate=initial_learning_rate,
        decay_steps=max(1, steps_per_epoch * epochs),
        alpha=0.08,
    )


def compile_model(
    model: tf.keras.Model,
    learning_rate_value,
    label_smoothing: float,
    optimizer_name: str,
    weight_decay: float,
) -> None:
    if optimizer_name == "adamw":
        optimizer = tf.keras.optimizers.AdamW(
            learning_rate=learning_rate_value,
            weight_decay=weight_decay,
        )
    else:
        optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate_value)

    model.compile(
        optimizer=optimizer,
        loss=tf.keras.losses.CategoricalCrossentropy(label_smoothing=label_smoothing),
        metrics=[
            "accuracy",
            tf.keras.metrics.TopKCategoricalAccuracy(k=3, name="top3_accuracy"),
        ],
    )


def unfreeze_tail(
    model: tf.keras.Model,
    architecture: str,
    fine_tune_layers: int,
    train_batchnorm: bool,
) -> None:
    base = next((layer for layer in model.layers if architecture in layer.name.lower()), None)
    if base is None:
        # Keras may name MobileNetV3Small "MobilenetV3small"; fall back to the nested model.
        base = next((layer for layer in model.layers if isinstance(layer, tf.keras.Model)), None)
    if base is None:
        raise SystemExit("Could not find MobileNet backbone to fine-tune")

    base.trainable = True
    trainable_from = max(0, len(base.layers) - fine_tune_layers)
    for index, layer in enumerate(base.layers):
        layer.trainable = index >= trainable_from and (
            train_batchnorm or not isinstance(layer, tf.keras.layers.BatchNormalization)
        )


def mobilenet_backbone(model: tf.keras.Model, architecture: str) -> tf.keras.Model | None:
    base = next((layer for layer in model.layers if architecture in layer.name.lower()), None)
    if base is not None and isinstance(base, tf.keras.Model):
        return base
    return next((layer for layer in model.layers if isinstance(layer, tf.keras.Model)), None)


def load_initial_backbone_weights(model: tf.keras.Model, architecture: str, model_path: Path | None) -> str | None:
    if model_path is None:
        return None
    source_model = tf.keras.models.load_model(model_path, compile=False)
    source_backbone = mobilenet_backbone(source_model, architecture)
    target_backbone = mobilenet_backbone(model, architecture)
    if source_backbone is None or target_backbone is None:
        raise SystemExit("Could not find MobileNet backbone in source or target model")
    if len(source_backbone.get_weights()) != len(target_backbone.get_weights()):
        raise SystemExit(
            "Initial backbone model is incompatible: backbone weight counts differ "
            f"({len(source_backbone.get_weights())} vs {len(target_backbone.get_weights())})"
        )
    target_backbone.set_weights(source_backbone.get_weights())
    return str(model_path)


def dataset_steps(dataset: tf.data.Dataset) -> int:
    cardinality = tf.data.experimental.cardinality(dataset).numpy()
    if cardinality < 0:
        return 1
    return int(max(1, cardinality))


def append_history(history: tf.keras.callbacks.History, prefix: str, next_history: tf.keras.callbacks.History) -> None:
    for key, values in next_history.history.items():
        history.history.setdefault(f"{prefix}_{key}", values)


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
    steps_per_epoch = dataset_steps(train_ds)

    model = build_model(args, labels)
    initial_backbone_model = load_initial_backbone_weights(model, args.architecture, args.initial_backbone_model)
    class_weights = load_class_weights(args, labels)
    fit_class_weights = class_weights
    train_ds = apply_mixup(train_ds, args.mixup_alpha)
    if class_weights and args.mixup_alpha > 0:
        train_ds = apply_sample_weights(train_ds, class_weights)
        fit_class_weights = None
    train_ds = train_ds.prefetch(tf.data.AUTOTUNE)
    validation_ds = validation_ds.prefetch(tf.data.AUTOTUNE)
    test_ds = test_ds.prefetch(tf.data.AUTOTUNE)
    compile_model(
        model,
        learning_rate(args.learning_rate, args.lr_schedule, args.epochs, steps_per_epoch),
        args.label_smoothing,
        args.optimizer,
        args.weight_decay,
    )

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor=args.monitor,
            patience=args.early_stopping_patience,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(args.output_root / "best.keras"),
            monitor=args.monitor,
            save_best_only=True,
        ),
    ]

    history = model.fit(
        train_ds,
        validation_data=validation_ds,
        epochs=args.epochs,
        callbacks=callbacks,
        class_weight=fit_class_weights,
        verbose=2,
    )

    if args.fine_tune_epochs > 0:
        unfreeze_tail(model, args.architecture, args.fine_tune_layers, args.fine_tune_batchnorm)
        compile_model(
            model,
            learning_rate(
                args.fine_tune_learning_rate,
                args.lr_schedule,
                args.fine_tune_epochs,
                steps_per_epoch,
            ),
            args.label_smoothing,
            args.optimizer,
            args.weight_decay,
        )
        fine_history = model.fit(
            train_ds,
            validation_data=validation_ds,
            epochs=args.fine_tune_epochs,
            callbacks=callbacks,
            class_weight=fit_class_weights,
            verbose=2,
        )
        append_history(history, "fine_tune", fine_history)

    if args.full_fine_tune_epochs > 0:
        unfreeze_tail(model, args.architecture, fine_tune_layers=10_000, train_batchnorm=args.fine_tune_batchnorm)
        compile_model(
            model,
            learning_rate(
                args.full_fine_tune_learning_rate,
                args.lr_schedule,
                args.full_fine_tune_epochs,
                steps_per_epoch,
            ),
            args.label_smoothing,
            args.optimizer,
            args.weight_decay,
        )
        full_fine_history = model.fit(
            train_ds,
            validation_data=validation_ds,
            epochs=args.full_fine_tune_epochs,
            callbacks=callbacks,
            class_weight=fit_class_weights,
            verbose=2,
        )
        append_history(history, "full_fine_tune", full_fine_history)

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
        "full_fine_tune_epochs": args.full_fine_tune_epochs,
        "full_fine_tune_learning_rate": args.full_fine_tune_learning_rate,
        "lr_schedule": args.lr_schedule,
        "optimizer": args.optimizer,
        "weight_decay": args.weight_decay,
        "augmentation_strength": args.augmentation_strength,
        "mixup_alpha": args.mixup_alpha,
        "label_smoothing": args.label_smoothing,
        "class_weight_json": str(args.class_weight_json) if args.class_weight_json else None,
        "class_weight_region": args.class_weight_region,
        "class_weight_strength": args.class_weight_strength,
        "class_weights": class_weights,
        "class_weight_application": (
            "sample_weight_after_mixup" if class_weights and args.mixup_alpha > 0 else "keras_class_weight"
            if class_weights
            else None
        ),
        "monitor": args.monitor,
        "early_stopping_patience": args.early_stopping_patience,
        "fine_tune_batchnorm": args.fine_tune_batchnorm,
        "initial_backbone_model": initial_backbone_model,
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
