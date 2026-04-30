# MobileNetV3Large Large-Scale Fish Auxiliary Experiment v1

Date: 2026-04-30

## Goal

Test whether the Kaggle Large-Scale Fish Dataset can improve the mobile species classifier.

## Dataset Handling

Only labels with clean app-taxonomy mappings were used for classification:

- `Sea Bass` -> `european-seabass`
- `Gilt-Head Bream` -> `gilthead-seabream`

Excluded from classification in this experiment:

- `Shrimp`: not a fish.
- `Trout`: ambiguous source label.
- `Black Sea Sprat`, `Hourse Mackerel`, `Red Mullet`, `Red Sea Bream`, `Striped Red Mullet`: useful for detector training or future taxonomy expansion, but not currently clean app classifier labels.

Prepared split:

```json
{
  "train": {
    "european-seabass": 700,
    "gilthead-seabream": 700
  },
  "validation": {
    "european-seabass": 150,
    "gilthead-seabream": 150
  },
  "test": {
    "european-seabass": 150,
    "gilthead-seabream": 150
  }
}
```

Important caveat: these are controlled market/supermarket images, not real angler photos.

## Auxiliary Run

Artifact:

`ml/artifacts/keras/mobilenet_v3_large_large_scale_mapped_v1_aux/final.keras`

Command:

```bash
ml/.venv-mobilenet/bin/python ml/scripts/train_keras_mobilenet_classifier.py \
  ml/data/classification/large_scale_fish_mapped_v1 \
  ml/artifacts/keras/mobilenet_v3_large_large_scale_mapped_v1_aux \
  --architecture mobilenet_v3_large \
  --weights imagenet \
  --image-size 224 \
  --batch-size 32 \
  --epochs 4 \
  --fine-tune-epochs 2 \
  --fine-tune-layers 40 \
  --optimizer adamw \
  --weight-decay 0.0001 \
  --augmentation-strength medium \
  --label-smoothing 0.03
```

Auxiliary test metrics:

```json
{
  "accuracy": 0.9933,
  "top3_accuracy": 1.0,
  "loss": 0.1083
}
```

This result is expected because the auxiliary task is two-class and visually controlled.

## North America Seeded Fine-Tune

Artifact:

`ml/artifacts/keras/mobilenet_v3_large_na_v2_aux_large_scale_seeded/final.keras`

The North America classifier was trained with the same architecture and class-weight setup as the current MobileNetV3Large baseline, but initialized from the auxiliary model's MobileNet backbone.

Command:

```bash
ml/.venv-mobilenet/bin/python ml/scripts/train_keras_mobilenet_classifier.py \
  ml/data/classification/inaturalist_na_v2 \
  ml/artifacts/keras/mobilenet_v3_large_na_v2_aux_large_scale_seeded \
  --architecture mobilenet_v3_large \
  --weights imagenet \
  --initial-backbone-model ml/artifacts/keras/mobilenet_v3_large_large_scale_mapped_v1_aux/final.keras \
  --image-size 224 \
  --batch-size 32 \
  --epochs 16 \
  --fine-tune-epochs 8 \
  --fine-tune-layers 80 \
  --optimizer adamw \
  --weight-decay 0.0001 \
  --augmentation-strength strong \
  --label-smoothing 0.05 \
  --class-weight-json ml/angler_priority_v1.json \
  --class-weight-region north-america \
  --class-weight-strength 0.5
```

Evaluator metrics on `inaturalist_na_v2` test:

```json
{
  "top1_accuracy": 0.7312,
  "top3_accuracy": 0.9313,
  "macro_recall": 0.7312,
  "priority_weighted_top1": 0.7012,
  "priority_weighted_top3": 0.927,
  "expected_calibration_error": 0.0315
}
```

Current full-image MobileNetV3Large benchmark:

```json
{
  "top1_accuracy": 0.7333,
  "top3_accuracy": 0.9292,
  "macro_recall": 0.7333,
  "priority_weighted_top1": 0.7092,
  "priority_weighted_top3": 0.9320
}
```

## Interpretation

The auxiliary dataset is useful for:

- adding clean Europe marine classes (`european-seabass`, `gilthead-seabream`);
- controlled-domain fish-shape pretraining;
- detector and localization work.

It did not improve the current North America classifier enough to replace the bundled app model. The priority-weighted score got worse, so this run should not be promoted to iOS.

Next classification data step: add more real angler or observation photos for app-priority species, especially black bass, trout/salmonids, and common coastal species. Use the large-scale fish data as supplemental pretraining only, not as a primary source for US classifier quality.
