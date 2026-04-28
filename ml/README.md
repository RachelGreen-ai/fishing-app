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
