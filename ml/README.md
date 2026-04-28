# Fish Species Model Workspace

This directory is for training assets and reproducible model runs.

Large files are intentionally ignored by git:

- `ml/data/`
- `ml/runs/`
- `ml/checkpoints/`
- `ml/artifacts/`

The app-facing artifact should be exported as `FishSpeciesClassifier.mlmodel` and then added to the iOS target. If the model is large, use Git LFS before committing it.

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
