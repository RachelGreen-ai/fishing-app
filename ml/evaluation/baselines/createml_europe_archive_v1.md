# Create ML Europe Archive Baseline v1

## Summary

This is the first real image-classifier baseline for the Europe archive seed split.

- Dataset: `ml/data/classification/europe_archive_v1`
- Source: local Europe archive / AFFiNe-style Kaggle drop
- Trainable labels: 29
- Skipped labels: `bitterling` because it has only 36 source images
- Split: 70% train, 15% validation, 15% test
- Seed: `20260428`
- Model type: Apple Create ML `MLImageClassifier`
- Iterations: 25
- Exported artifact: `ml/artifacts/createml/europe_archive_v1/FishSpeciesClassifier.mlmodel` (ignored by git)

## Commands

```bash
python3 ml/scripts/create_classification_split.py \
  ml/data/benchmarks/europe_archive_seed_v1/manifest.jsonl \
  ml/data/classification/europe_archive_v1 \
  --mode symlink \
  --min-per-class 50 \
  --train 0.7 \
  --validation 0.15 \
  --test 0.15 \
  --seed 20260428 \
  --labels-json ml/fish_species_europe_v1.labels.json \
  --taxonomy-json ml/fish_species_europe_v1.taxonomy.json

xcrun swift ml/scripts/train_createml_image_classifier.swift \
  ml/data/classification/europe_archive_v1 \
  ml/artifacts/createml/europe_archive_v1/FishSpeciesClassifier.mlmodel \
  25

xcrun swift ml/scripts/predict_coreml_image_classifier.swift \
  ml/artifacts/createml/europe_archive_v1/FishSpeciesClassifier.mlmodel \
  ml/data/classification/europe_archive_v1/test.manifest.jsonl \
  ml/data/classification/europe_archive_v1 \
  ml/runs/createml/europe_archive_v1/test_predictions.jsonl

python3 ml/scripts/evaluate_predictions.py \
  ml/data/classification/europe_archive_v1/test.manifest.jsonl \
  ml/runs/createml/europe_archive_v1/test_predictions.jsonl

python3 ml/scripts/evaluate_predictions.py \
  ml/data/classification/europe_archive_v1/test.manifest.jsonl \
  ml/runs/createml/europe_archive_v1/test_predictions.jsonl \
  --prior-json ml/angler_priority_v1.json \
  --prior-region europe
```

## Metrics

No threshold:

- Test examples: 1,118
- Coverage: 100.00%
- Top-1 accuracy: 57.25%
- Top-3 accuracy: 78.53%
- Macro recall: 52.46%
- Expected calibration error: 3.68%
- Mean prediction latency: 3.43 ms
- Europe angler-priority weighted top-1 accuracy: 61.03%
- Europe angler-priority weighted top-3 accuracy: 76.67%
- Europe prior coverage in this split: 84.80%

Create ML built-in test accuracy:

- 56.80%

Threshold `0.70`:

- Coverage: 38.10%
- Selective top-1 accuracy: 87.56%
- Top-1 over all known examples: 33.36%
- Top-3 over all known examples: 36.05%
- Macro recall: 29.72%
- Europe angler-priority weighted coverage: 44.29%
- Europe angler-priority weighted selective top-1 accuracy: 89.09%

Threshold `0.90`:

- Coverage: 20.66%
- Selective top-1 accuracy: 95.24%
- Top-1 over all known examples: 19.68%
- Top-3 over all known examples: 20.04%
- Macro recall: 16.55%
- Europe angler-priority weighted coverage: 25.12%
- Europe angler-priority weighted selective top-1 accuracy: 94.17%

Missing from Europe prior coverage because this archive split does not include those labels:

- `atlantic-herring`
- `atlantic-mackerel`
- `atlantic-salmon`
- `bitterling`
- `blue-whiting`
- `cod`
- `european-grayling`
- `european-seabass`
- `gilthead-seabream`
- `plaice`

## Best And Weakest Species

Strong species by top-1 recall:

- `european-eel`: 87.50%
- `sturgeon`: 86.36%
- `tench`: 85.42%
- `pumpkinseed`: 83.78%
- `common-barbel`: 76.47%
- `common-carp`: 76.40%

Weak species by top-1 recall:

- `common-dace`: 0.00%
- `vimba-bream`: 0.00%
- `asp`: 23.08%
- `monkey-goby`: 25.00%
- `roach`: 25.53%
- `chub`: 27.91%
- `bighead-goby`: 28.57%

## Lookalike Group Metrics

- `roach-rudd-bream`: 37.99% top-1, 65.92% top-3
- `asp-chub-ide-dace`: 29.03% top-1, 65.81% top-3
- `neogobius-gobies`: 42.42% top-1, 81.82% top-3
- `perch-ruffe-zander`: 55.46% top-1, 74.79% top-3
- `carp-crucian-grass`: 62.20% top-1, 84.21% top-3

## Interpretation

This baseline does not meet MVP requirements. It is useful as a starting model and a proof that the local Create ML pipeline works.

The high-confidence behavior is encouraging: at a 0.90 threshold, selective accuracy is above 95%, but coverage drops to about 21%. That suggests the app should use abstention and ask for better evidence rather than forcing an ID when the image model is not confident.

Priority improvement areas:

- Treat this as an imbalanced deployment problem, with both balanced macro metrics and angler-priority weighted metrics.
- Add or promote training data for high-priority Europe species missing from the archive split: `cod`, `european-seabass`, `atlantic-salmon`, `european-grayling`, `plaice`, and `gilthead-seabream`.
- Add more data or merge sparse labels such as `common-dace`, `vimba-bream`, and `bighead-goby`.
- Improve high-priority lookalike groups, especially `roach-rudd-bream`, `perch-ruffe-zander`, and `asp-chub-ide-dace`.
- Add unknown/out-of-scope examples so abstention recall can be measured.
- Train a stronger PyTorch/Core ML model after this Create ML baseline.
- Review label quality in citizen-science source images before promoting anything to final gold.
