# Fish Species Model Workspace

This directory is for training assets and reproducible model runs.

Large files are intentionally ignored by git:

- `ml/data/`
- `ml/runs/`
- `ml/checkpoints/`
- `ml/artifacts/`
- `ml/.venv-mobilenet/`
- `ml/.venv-yolo/`

Create ML exports should be named `FishSpeciesClassifier.mlmodel`; Keras/Core ML Tools MobileNet exports should be named `FishSpeciesClassifier.mlpackage`. Add the chosen artifact to the iOS target. If the model is large, use Git LFS before committing it.

The current iOS app already contains a Core ML/Vision adapter in `ios/FishingApp/FishImageClassifier.swift`.

Dataset source notes and prioritization live in `docs/datasets/fish-dataset-registry.md`.

Validate a prepared dataset before training:

```bash
python3 ml/scripts/validate_dataset.py ml/data/fish_species_v1 ml/fish_species_v1.labels.json --min-train 500 --min-validation 100 --min-test 100
```

Prepare the QUT FISH Kaggle dataset as a seed benchmark source:

```bash
python3 ml/scripts/prepare_qut_kaggle_seed.py \
  ml/data/sources/qut_fish_kaggle \
  ml/data/benchmarks/qut_fish_seed_v1 \
  --mode manifest-only
```

Create a reproducible classification split from the Europe archive seed:

```bash
python3 ml/scripts/create_classification_split.py \
  ml/data/benchmarks/europe_archive_seed_v1/manifest.jsonl \
  ml/data/classification/europe_archive_v1 \
  --mode symlink \
  --min-per-class 50 \
  --labels-json ml/fish_species_europe_v1.labels.json \
  --taxonomy-json ml/fish_species_europe_v1.taxonomy.json
```

Prepare the North America iNaturalist seed:

```bash
python3 ml/scripts/prepare_inaturalist_seed.py \
  ml/data/benchmarks/inaturalist_na_seed_v1 \
  --max-per-species 160 \
  --min-per-species 80 \
  --image-size medium
```

Create a reproducible North America split:

```bash
python3 ml/scripts/create_classification_split.py \
  ml/data/benchmarks/inaturalist_na_seed_v1/manifest.jsonl \
  ml/data/classification/inaturalist_na_v1 \
  --mode symlink \
  --min-per-class 80 \
  --labels-json ml/fish_species_v1.labels.json \
  --taxonomy-json ml/fish_species_v1.taxonomy.json
```

Validate label hierarchy:

```bash
python3 ml/scripts/validate_label_taxonomy.py \
  ml/fish_species_europe_v1.taxonomy.json \
  --labels-json ml/fish_species_europe_v1.labels.json \
  --aliases-json ml/fish_species_europe_v1.aliases.json
```

Train a first local Create ML baseline:

```bash
xcrun swift ml/scripts/train_createml_image_classifier.swift \
  ml/data/classification/europe_archive_v1 \
  ml/artifacts/createml/europe_archive_v1/FishSpeciesClassifier.mlmodel \
  25
```

Train the North America Create ML baseline:

```bash
xcrun swift ml/scripts/train_createml_image_classifier.swift \
  ml/data/classification/inaturalist_na_v1 \
  ml/artifacts/createml/inaturalist_na_v1/FishSpeciesClassifier.mlmodel \
  25
```

Train a MobileNetV3Small baseline:

```bash
/Users/junyishen/.local/bin/uv venv ml/.venv-mobilenet --python /opt/homebrew/bin/python3.11
/Users/junyishen/.local/bin/uv pip install --python ml/.venv-mobilenet/bin/python -r ml/requirements-mobilenet.txt

ml/.venv-mobilenet/bin/python ml/scripts/train_keras_mobilenet_classifier.py \
  ml/data/classification/inaturalist_na_v2 \
  ml/artifacts/keras/mobilenet_v3_small_na_v2 \
  --architecture mobilenet_v3_small \
  --weights imagenet \
  --epochs 20 \
  --fine-tune-epochs 10 \
  --fine-tune-layers 40 \
  --export-coreml
```

The MobileNet Core ML export writes `FishSpeciesClassifier.mlpackage`.

Export an already-trained Keras classifier to Core ML:

```bash
ml/.venv-mobilenet/bin/python ml/scripts/export_keras_classifier_to_coreml.py \
  ml/artifacts/keras/mobilenet_v3_large_na_v2_weighted_smooth/final.keras \
  ml/artifacts/keras/mobilenet_v3_large_na_v2_weighted_smooth/labels.json \
  ios/FishingApp/FishSpeciesClassifier.mlpackage
```

Train the current best MobileNetV3Large weighted/smoothed baseline:

```bash
ml/.venv-mobilenet/bin/python ml/scripts/train_keras_mobilenet_classifier.py \
  ml/data/classification/inaturalist_na_v2 \
  ml/artifacts/keras/mobilenet_v3_large_na_v2_weighted_smooth \
  --architecture mobilenet_v3_large \
  --weights imagenet \
  --epochs 16 \
  --fine-tune-epochs 8 \
  --fine-tune-layers 80 \
  --batch-size 32 \
  --label-smoothing 0.05 \
  --class-weight-json ml/angler_priority_v1.json \
  --class-weight-region north-america \
  --class-weight-strength 0.5 \
  --fine-tune-learning-rate 7e-6
```

Train a YOLO26 classification baseline:

```bash
/Users/junyishen/.local/bin/uv venv ml/.venv-yolo --python /opt/homebrew/bin/python3.11
/Users/junyishen/.local/bin/uv pip install --python ml/.venv-yolo/bin/python -r ml/requirements-yolo.txt

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

Run predictions for evaluator metrics:

```bash
xcrun swift ml/scripts/predict_coreml_image_classifier.swift \
  ml/artifacts/createml/europe_archive_v1/FishSpeciesClassifier.mlmodel \
  ml/data/classification/europe_archive_v1/test.manifest.jsonl \
  ml/data/classification/europe_archive_v1 \
  ml/runs/createml/europe_archive_v1/test_predictions.jsonl

python3 ml/scripts/evaluate_predictions.py \
  ml/data/classification/europe_archive_v1/test.manifest.jsonl \
  ml/runs/createml/europe_archive_v1/test_predictions.jsonl
```

Evaluate against the app's initial angler-priority prior:

```bash
python3 ml/scripts/evaluate_predictions.py \
  ml/data/classification/europe_archive_v1/test.manifest.jsonl \
  ml/runs/createml/europe_archive_v1/test_predictions.jsonl \
  --prior-json ml/angler_priority_v1.json \
  --prior-region europe
```
