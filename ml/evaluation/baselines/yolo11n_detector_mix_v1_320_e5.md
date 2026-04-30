# YOLO11n Fish Detector Mix v1, 320px, 5 Epochs

Date: 2026-04-30

## Goal

Train a lightweight mobile-friendly fish-first detector that can support capture UX, fish localization, and crop-before-classify experiments.

## Training Data

Mixed detection manifest:

- NOAA Labeled Fishes in the Wild seed: 1,473 rows.
- Kaggle Large-Scale Fish Dataset segmentation seed: 8,000 fish rows.
- Total merged rows: 9,473.
- Total ground-truth boxes: 8,929.

Large-scale fish dataset handling:

- Used GT segmentation masks to derive fish bounding boxes.
- Skipped `Shrimp` by default because it is not a fish and would weaken a fish-first detector.
- Kept 8 fish-like seafood classes from the source dataset.
- Only `Sea Bass` and `Gilt-Head Bream` currently map into the app taxonomy for classification enrichment; the rest are detector-only until taxonomy expansion.

Important caveat: the Kaggle data is controlled market/supermarket imagery, not in-the-wild angler photos. It is useful for fish localization pretraining, but app-facing validation still needs wild/mobile photos.

## Training Command

```bash
YOLO_CONFIG_DIR=/tmp/Ultralytics ml/.venv-yolo/bin/yolo detect train \
  data=ml/data/detection/fish_detector_mix_v1/yolo/dataset.yaml \
  model=ml/artifacts/yolo/yolo11n.pt \
  epochs=5 \
  imgsz=320 \
  batch=16 \
  device=cpu \
  project=$PWD/ml/artifacts/yolo \
  name=fish_detector_mix_v1_yolo11n_320_e5 \
  exist_ok=True \
  patience=3 \
  workers=0
```

Best weights:

`ml/artifacts/yolo/fish_detector_mix_v1_yolo11n_320_e5/weights/best.pt`

## Detector Validation

Ultralytics validation on the held-out mixed YOLO split:

```json
{
  "images": 1309,
  "instances": 1327,
  "precision": 0.984,
  "recall": 0.934,
  "map50": 0.964,
  "map50_95": 0.851
}
```

Independent manifest evaluator at score threshold 0.25 and IoU 0.5:

```json
{
  "image_count": 8725,
  "ground_truth_box_count": 8929,
  "predicted_box_count": 8824,
  "precision": 0.957,
  "recall": 0.9458,
  "f1": 0.9514,
  "positive_image_recall": 0.979,
  "negative_image_false_positive_rate": 0.0476,
  "mean_matched_iou": 0.9364,
  "mean_latency_ms": 12.88
}
```

## Crop-Before-Classify Check

Existing classifier:

`ml/artifacts/keras/mobilenet_v3_large_na_v2_weighted_smooth/final.keras`

Baseline full-image classifier on `inaturalist_na_v2` test:

```json
{
  "top1_accuracy": 0.7333,
  "top3_accuracy": 0.9292,
  "macro_recall": 0.7333,
  "priority_weighted_top1": 0.7092,
  "priority_weighted_top3": 0.9320
}
```

Detector crops at score threshold 0.25, padding 0.08, fallback full image:

```json
{
  "detected_crops": 297,
  "fallback_full_images": 183,
  "top1_accuracy": 0.7125,
  "top3_accuracy": 0.9104,
  "macro_recall": 0.7125,
  "priority_weighted_top1": 0.6895,
  "priority_weighted_top3": 0.9132
}
```

Detector crops at score threshold 0.50, padding 0.08, fallback full image:

```json
{
  "detected_crops": 225,
  "fallback_full_images": 255,
  "top1_accuracy": 0.7083,
  "top3_accuracy": 0.9167,
  "macro_recall": 0.7083,
  "priority_weighted_top1": 0.6972,
  "priority_weighted_top3": 0.9233
}
```

Detector crops at score threshold 0.25, padding 0.25, fallback full image:

```json
{
  "detected_crops": 297,
  "fallback_full_images": 183,
  "top1_accuracy": 0.7188,
  "top3_accuracy": 0.9250,
  "macro_recall": 0.7188,
  "priority_weighted_top1": 0.7003,
  "priority_weighted_top3": 0.9315
}
```

## Interpretation

The mixed detector is strong enough to keep for fish-first UX and future segmentation/cropping work. It is fast and localizes fish reliably on the detection benchmark.

However, feeding detector crops into the current MobileNetV3Large classifier reduces top-1 accuracy on the North America test split. The current classifier was trained on full images, so the crop distribution is mismatched.

Next ML step: fine-tune the classifier with detector-style crops and full-image mixup, then re-run this same crop benchmark. Until that improves, the app should use the detector for UX/localization and keep full-frame classification as the default species decision path.
