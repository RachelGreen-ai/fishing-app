# MobileNetV3Large North America Priority-5 Enrichment v3

Date: 2026-04-30

## Goal

Improve the real app classifier with more app-relevant, species-labeled field photos after controlled large-scale fish imagery failed to improve the North America benchmark.

## Data Added

Downloaded 3,750 new licensed iNaturalist research-grade images, excluding all observations already present in `inaturalist_na_seed_v2`.

Priority-5 enrichment classes:

```json
{
  "largemouth-bass": 750,
  "smallmouth-bass": 750,
  "spotted-bass": 750,
  "rainbow-trout": 750,
  "channel-catfish": 750
}
```

The enriched classifier dataset keeps the existing `inaturalist_na_v2` test manifest frozen and uses the new images only for train/validation.

Resulting split:

```json
{
  "train": {
    "bluegill": 280,
    "channel-catfish": 918,
    "largemouth-bass": 918,
    "rainbow-trout": 918,
    "red-drum": 280,
    "red-snapper": 280,
    "smallmouth-bass": 918,
    "spotted-bass": 918
  },
  "validation": {
    "bluegill": 60,
    "channel-catfish": 172,
    "largemouth-bass": 172,
    "rainbow-trout": 172,
    "red-drum": 60,
    "red-snapper": 60,
    "smallmouth-bass": 172,
    "spotted-bass": 172
  },
  "test": {
    "bluegill": 60,
    "channel-catfish": 60,
    "largemouth-bass": 60,
    "rainbow-trout": 60,
    "red-drum": 60,
    "red-snapper": 60,
    "smallmouth-bass": 60,
    "spotted-bass": 60
  }
}
```

## Training

The run starts from the current best MobileNetV3Large model and continues training locally on the enriched split.

```bash
ml/.venv-mobilenet/bin/python ml/scripts/train_keras_mobilenet_classifier.py \
  ml/data/classification/inaturalist_na_v3_priority5 \
  ml/artifacts/keras/mobilenet_v3_large_na_v3_priority5_continued \
  --architecture mobilenet_v3_large \
  --weights none \
  --initial-model ml/artifacts/keras/mobilenet_v3_large_na_v2_weighted_smooth/final.keras \
  --image-size 224 \
  --batch-size 32 \
  --epochs 8 \
  --fine-tune-epochs 8 \
  --fine-tune-layers 100 \
  --learning-rate 0.0001 \
  --fine-tune-learning-rate 0.000005 \
  --optimizer adamw \
  --weight-decay 0.0001 \
  --augmentation-strength medium \
  --label-smoothing 0.05 \
  --class-weight-json ml/angler_priority_v1.json \
  --class-weight-region north-america \
  --class-weight-strength 0.5
```

Keras test metrics on the frozen v2 test folder:

```json
{
  "accuracy": 0.7583,
  "top3_accuracy": 0.9271,
  "loss": 0.9079
}
```

## Evaluator Metrics

Frozen `inaturalist_na_v2` test manifest:

```json
{
  "top1_accuracy": 0.7542,
  "top3_accuracy": 0.9354,
  "macro_recall": 0.7542,
  "priority_weighted_top1": 0.7395,
  "priority_weighted_top3": 0.9267,
  "expected_calibration_error": 0.0315,
  "mean_latency_ms": 28.92
}
```

Current best full-image MobileNetV3Large benchmark:

```json
{
  "top1_accuracy": 0.7333,
  "top3_accuracy": 0.9292,
  "macro_recall": 0.7333,
  "priority_weighted_top1": 0.7092,
  "priority_weighted_top3": 0.9320
}
```

Per-species top-1 recall:

```json
{
  "bluegill": 0.7167,
  "channel-catfish": 0.8667,
  "largemouth-bass": 0.6667,
  "rainbow-trout": 0.7000,
  "red-drum": 0.7500,
  "red-snapper": 0.8833,
  "smallmouth-bass": 0.7500,
  "spotted-bass": 0.7000
}
```

Lookalike-group top-1:

```json
{
  "black-bass": 0.7056,
  "catfish": 0.8667,
  "lepomis-sunfish": 0.7167,
  "red-coastal": 0.8167,
  "trout-salmonid": 0.7000
}
```

## Interpretation

Priority-5 enrichment is the first data path that clearly improves the real North America classifier benchmark. It improves top-1, top-3, macro recall, black-bass recall, catfish recall, trout recall, and priority-weighted top-1.

Do not promote automatically yet because priority-weighted top-3 dipped from 0.9320 to 0.9267. The likely issue is that bluegill, a tier-1 priority species, was not part of this enrichment pass and its top-3 recall is lower in this model.

Recommended next run:

1. Add bluegill enrichment to balance tier-1 priority coverage.
2. Consider red drum/red snapper enrichment if coastal performance matters for the MVP region.
3. Re-run the same continued-training path and promote only if priority-weighted top-3 recovers while preserving the new top-1 gains.
