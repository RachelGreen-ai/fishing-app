# MobileNetV3Large North America Priority-6 Enrichment v3

Date: 2026-05-01

## Goal

Recover priority-weighted top-3 after the priority-5 enrichment run by adding
bluegill, a tier-1 North America angler species that was still underrepresented.

## Data Added

Priority-6 uses the same 3,750 priority-5 iNaturalist enrichment images plus
750 new licensed bluegill images. All enrichment downloads exclude observations
already present in `inaturalist_na_seed_v2`.

Additional priority-6 class:

```json
{
  "bluegill": 750
}
```

The enriched classifier dataset keeps the existing `inaturalist_na_v2` test
manifest frozen and uses the new images only for train/validation.

Resulting split:

```json
{
  "train": {
    "bluegill": 918,
    "channel-catfish": 918,
    "largemouth-bass": 918,
    "rainbow-trout": 918,
    "red-drum": 280,
    "red-snapper": 280,
    "smallmouth-bass": 918,
    "spotted-bass": 918
  },
  "validation": {
    "bluegill": 172,
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

The run starts from the current best MobileNetV3Large model and continues
training locally on the priority-6 enriched split.

```bash
ml/.venv-mobilenet/bin/python ml/scripts/train_keras_mobilenet_classifier.py \
  ml/data/classification/inaturalist_na_v3_priority6 \
  ml/artifacts/keras/mobilenet_v3_large_na_v3_priority6_continued \
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
  --class-weight-strength 0.5 \
  --monitor val_accuracy \
  --early-stopping-patience 4
```

Keras test metrics on the frozen v2 test folder:

```json
{
  "accuracy": 0.7708,
  "top3_accuracy": 0.9312,
  "loss": 0.8960
}
```

## Evaluator Metrics

Frozen `inaturalist_na_v2` test manifest:

```json
{
  "top1_accuracy": 0.7688,
  "top3_accuracy": 0.9375,
  "macro_recall": 0.7688,
  "priority_weighted_top1": 0.7632,
  "priority_weighted_top3": 0.9345,
  "expected_calibration_error": 0.0584,
  "mean_latency_ms": 30.47
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
  "bluegill": 0.8167,
  "channel-catfish": 0.8500,
  "largemouth-bass": 0.7000,
  "rainbow-trout": 0.7000,
  "red-drum": 0.7167,
  "red-snapper": 0.8667,
  "smallmouth-bass": 0.7667,
  "spotted-bass": 0.7333
}
```

Lookalike-group top-1:

```json
{
  "black-bass": 0.7333,
  "catfish": 0.8500,
  "lepomis-sunfish": 0.8167,
  "red-coastal": 0.7917,
  "trout-salmonid": 0.7000
}
```

Confidence-threshold sweep:

| Threshold | Coverage | Selective top-1 | Priority selective top-1 |
| --- | ---: | ---: | ---: |
| 0.00 | 1.0000 | 0.7688 | 0.7632 |
| 0.50 | 0.8250 | 0.8510 | 0.8489 |
| 0.60 | 0.7063 | 0.8820 | 0.8855 |
| 0.70 | 0.5917 | 0.9401 | 0.9353 |
| 0.80 | 0.4917 | 0.9619 | 0.9616 |
| 0.90 | 0.3333 | 0.9625 | 0.9602 |

## Interpretation

Priority-6 is the first enrichment run that beats the current full-image
MobileNetV3Large benchmark on top-1, top-3, macro recall, priority-weighted
top-1, and priority-weighted top-3. Bluegill enrichment fixed the main
priority-weighted top-3 regression from priority-5 and improved the
lepomis-sunfish lookalike group from 0.7167 to 0.8167 top-1 recall.

This is a promotable iOS classifier candidate. The main caveat is calibration:
ECE increased to 0.0584, so the app should keep cautious confidence language
and treat only high-confidence image predictions as strong evidence. At a 0.70
threshold, selective top-1 is 0.9401 with 0.5917 coverage, which is useful for
the "likely" tier while still allowing the hybrid engine to ask for better
evidence on uncertain catches.
