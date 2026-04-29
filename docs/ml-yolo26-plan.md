# YOLO26 Model Plan

YOLO26 is worth evaluating for two different jobs in the fishing app:

1. Species classification with `yolo26*-cls.pt`.
2. Fish detection/cropping with `yolo26*.pt` or `yolo26*-seg.pt`.

The first job competes with MobileNet and Create ML on species ID. The second job is complementary: it can find the fish in a messy angler photo, crop the classifier input, reject photos with no fish, and eventually support size estimation when paired with a reference object or camera metadata.

## Current Candidates

- `yolo26n-cls.pt`: first mobile/edge classifier candidate.
- `yolo26s-cls.pt`: next classifier if nano underfits.
- `yolo26n.pt`: first fish detector candidate after we have box labels.
- `yolo26n-seg.pt`: possible future mask model for better length estimation.

## Roboflow Fish Detection Dataset

Dataset inspected: https://universe.roboflow.com/fish-detection-d7azy/fish-dataset-8ulfi/dataset/11

Useful facts from the public page:

- Project type: object detection.
- Version: v11, generated Jun 16, 2024.
- Total images: 1,876.
- Split: 1,110 train, 630 validation, 136 test.
- Formats include YOLO26 TXT annotations plus YAML config.
- Preprocessing: auto-orient and stretch resize to 640x640.
- Augmentations: none.

This dataset is promising for fish localization, crop-before-identify, and size/length experiments. It should not be mixed into the species classifier benchmark unless we confirm species-level labels, because many detection datasets label only `fish`.

## Training

Set up the isolated YOLO environment:

```bash
/Users/junyishen/.local/bin/uv venv ml/.venv-yolo --python /opt/homebrew/bin/python3.11
/Users/junyishen/.local/bin/uv pip install --python ml/.venv-yolo/bin/python -r ml/requirements-yolo.txt
```

Train the first YOLO26 classifier:

```bash
YOLO_CONFIG_DIR=/tmp/Ultralytics ml/.venv-yolo/bin/yolo classify train \
  data=ml/data/classification/inaturalist_na_v2 \
  model=yolo26n-cls.pt \
  epochs=30 \
  imgsz=224 \
  batch=32 \
  device=cpu \
  project=ml/artifacts/yolo \
  name=yolo26n_cls_na_v2 \
  exist_ok=True \
  patience=5
```

Evaluate with the app benchmark:

```bash
ml/.venv-yolo/bin/python ml/scripts/predict_ultralytics_classifier.py \
  ml/artifacts/yolo/yolo26n_cls_na_v2/weights/best.pt \
  ml/data/classification/inaturalist_na_v2/test.manifest.jsonl \
  ml/data/classification/inaturalist_na_v2 \
  ml/runs/yolo/yolo26n_cls_na_v2/test_predictions.jsonl

python3 ml/scripts/evaluate_predictions.py \
  ml/data/classification/inaturalist_na_v2/test.manifest.jsonl \
  ml/runs/yolo/yolo26n_cls_na_v2/test_predictions.jsonl \
  --prior-json ml/angler_priority_v1.json \
  --prior-region north-america
```

## Sources

- YOLO26 docs: https://docs.ultralytics.com/models/yolo26/
- YOLO classification docs: https://docs.ultralytics.com/tasks/classify/
- Roboflow dataset: https://universe.roboflow.com/fish-detection-d7azy/fish-dataset-8ulfi/dataset/11
