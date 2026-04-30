# YOLO11n Fish Detector NOAA LFIW Smoke Baseline

This is a one-epoch CPU smoke run, not a candidate app model. It verifies that
the detection dataset conversion, Ultralytics training path, prediction writer,
and evaluator work end to end.

## Dataset

- Source manifest: `ml/data/detection/noaa_lfiw_seed_v1/manifest.jsonl`
- YOLO dataset: `ml/data/detection/noaa_lfiw_yolo_v1`
- Usable rows: 725
- Skipped positive-source rows with no boxes: 748
- Train/val/test rows: 507 / 109 / 109
- Train/val/test boxes: 702 / 122 / 105
- Class: `fish`

Rows from the positive source without annotations are skipped by default because
treating visible-but-unboxed fish as background would poison the detector.

## Smoke Train

```bash
YOLO_CONFIG_DIR=/tmp/Ultralytics ml/.venv-yolo/bin/yolo detect train \
  data=ml/data/detection/noaa_lfiw_yolo_v1/dataset.yaml \
  model=yolo11n.pt \
  epochs=1 \
  imgsz=320 \
  batch=8 \
  device=cpu \
  project=ml/artifacts/yolo \
  name=fish_detector_noaa_lfiw_v1_smoke \
  exist_ok=True \
  patience=1 \
  workers=0
```

Ultralytics nested the relative `project` path under `runs/detect` for this
smoke command. Use `project=$PWD/ml/artifacts/yolo` for the real run.

## Ultralytics Val Metrics

- Precision: 1.0000
- Recall: 0.1271
- mAP50: 0.2903
- mAP50-95: 0.1468
- Reported CPU inference: 26.5 ms/image at 320 px

## JSONL Evaluator Metrics

Predictions generated at `conf=0.001`; evaluator threshold varied:

| Score threshold | Precision | Recall | F1 | Positive image recall | Negative image FP rate | Mean matched IoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.001 | 0.0494 | 0.3854 | 0.0875 | 0.6055 | 1.0000 | 0.7953 |
| 0.010 | 0.0494 | 0.3854 | 0.0875 | 0.6055 | 1.0000 | 0.7953 |
| 0.050 | 0.7500 | 0.1163 | 0.2013 | 0.1869 | 0.0136 | 0.8185 |

At the normal 0.25 threshold this one-epoch model emitted no detections. The
next useful run is a real 40+ epoch fine tune at 640 px, followed by
crop-before-classify evaluation on the MobileNet classifier.

## Crop-Before-Classify Smoke Check

The smoke detector was run against
`ml/data/classification/inaturalist_na_v2/test.manifest.jsonl` at `conf=0.05`,
then `crop_manifest_with_detections.py` built a cropped benchmark manifest.

- Input rows: 480
- Detector crops: 98
- Full-image fallbacks: 382
- Skipped rows: 0

Current MobileNetV3Large weighted/smoothed baseline on the original test set:

- Top-1: 0.7333
- Top-3: 0.9292
- Macro recall: 0.7333
- North America priority-weighted top-1: 0.7092
- North America priority-weighted top-3: 0.9320

MobileNetV3Large on the smoke detector crop manifest:

- Top-1: 0.7125
- Top-3: 0.9229
- Macro recall: 0.7125
- North America priority-weighted top-1: 0.6848
- North America priority-weighted top-3: 0.9208

The one-epoch detector hurts classification, which is expected. The value of
this smoke check is that the detector -> crop manifest -> classifier -> metrics
loop now exists and can be reused for every real detector candidate.
