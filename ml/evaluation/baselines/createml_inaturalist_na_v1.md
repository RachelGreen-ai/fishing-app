# Create ML North America iNaturalist Baseline v1

## Summary

This is the first North America MVP classification seed and planned Create ML baseline.

- Dataset: `ml/data/classification/inaturalist_na_v1`
- Source: public iNaturalist research-grade observations
- Seed source root: `ml/data/benchmarks/inaturalist_na_seed_v1`
- Trainable labels: 8
- Skipped labels: none
- Split: 70% train, 15% validation, 15% test
- Seed: `20260428`
- Per-species split: 112 train, 24 validation, 24 test
- Model type: Apple Create ML `MLImageClassifier`
- Iterations: 25
- Exported artifact: `ml/artifacts/createml/inaturalist_na_v1/FishSpeciesClassifier.mlmodel` (ignored by git)

## Dataset Preparation

```bash
python3 ml/scripts/prepare_inaturalist_seed.py \
  ml/data/benchmarks/inaturalist_na_seed_v1 \
  --max-per-species 160 \
  --min-per-species 80 \
  --image-size medium
```

Downloaded 1,280 licensed public images:

| Species | Images |
| --- | ---: |
| `largemouth-bass` | 160 |
| `smallmouth-bass` | 160 |
| `spotted-bass` | 160 |
| `bluegill` | 160 |
| `rainbow-trout` | 160 |
| `channel-catfish` | 160 |
| `red-drum` | 160 |
| `red-snapper` | 160 |

## Split

```bash
python3 ml/scripts/create_classification_split.py \
  ml/data/benchmarks/inaturalist_na_seed_v1/manifest.jsonl \
  ml/data/classification/inaturalist_na_v1 \
  --mode symlink \
  --min-per-class 80 \
  --train 0.7 \
  --validation 0.15 \
  --test 0.15 \
  --seed 20260428 \
  --labels-json ml/fish_species_v1.labels.json \
  --taxonomy-json ml/fish_species_v1.taxonomy.json

python3 ml/scripts/validate_dataset.py \
  ml/data/classification/inaturalist_na_v1 \
  ml/data/classification/inaturalist_na_v1/labels.json \
  --min-train 100 \
  --min-validation 20 \
  --min-test 20
```

Validation passed.

## Training Command

```bash
xcrun swift ml/scripts/train_createml_image_classifier.swift \
  ml/data/classification/inaturalist_na_v1 \
  ml/artifacts/createml/inaturalist_na_v1/FishSpeciesClassifier.mlmodel \
  25
```

Training completed from the user's terminal and wrote:

- `ml/artifacts/createml/inaturalist_na_v1/FishSpeciesClassifier.mlmodel` (ignored by git)

Create ML training report:

```text
******PRECISION RECALL******
----------------------------------
Class           Precision(%) Recall(%)
bluegill        68.42        54.17
channel-catfish 53.85        58.33
largemouth-bass 44.44        50.00
rainbow-trout   61.54        66.67
red-drum        50.00        66.67
red-snapper     85.71        75.00
smallmouth-bass 40.00        33.33
spotted-bass    47.62        41.67
```

## Prediction And Evaluation Commands

```bash
xcrun swift ml/scripts/predict_coreml_image_classifier.swift \
  ml/artifacts/createml/inaturalist_na_v1/FishSpeciesClassifier.mlmodel \
  ml/data/classification/inaturalist_na_v1/test.manifest.jsonl \
  ml/data/classification/inaturalist_na_v1 \
  ml/runs/createml/inaturalist_na_v1/test_predictions.jsonl

python3 ml/scripts/evaluate_predictions.py \
  ml/data/classification/inaturalist_na_v1/test.manifest.jsonl \
  ml/runs/createml/inaturalist_na_v1/test_predictions.jsonl \
  --prior-json ml/angler_priority_v1.json \
  --prior-region north-america
```

## Metrics

Saved-model evaluator, no threshold:

- Test examples: 192.
- Coverage: 100.00%.
- Top-1 accuracy: 58.33%.
- Top-3 accuracy: 83.85%.
- Macro recall: 58.33%.
- Expected calibration error: 21.28%.
- Mean prediction latency: 4.79 ms.
- North America angler-priority weighted top-1 accuracy: 59.08%.
- North America angler-priority weighted top-3 accuracy: 85.33%.
- North America prior coverage in this split: 100.00%.

Threshold `0.70`:

- Coverage: 68.23%.
- Selective top-1 accuracy: 71.76%.
- Top-1 over all known examples: 48.96%.
- Top-3 over all known examples: 62.50%.
- Macro recall: 48.96%.
- North America angler-priority weighted coverage: 67.58%.
- North America angler-priority weighted selective top-1 accuracy: 73.12%.

Threshold `0.90`:

- Coverage: 43.75%.
- Selective top-1 accuracy: 79.76%.
- Top-1 over all known examples: 34.90%.
- Top-3 over all known examples: 40.62%.
- Macro recall: 34.90%.
- North America angler-priority weighted coverage: 42.08%.
- North America angler-priority weighted selective top-1 accuracy: 78.61%.

## Per-Species Saved-Model Metrics

| Species | Precision | Top-1 Recall | Top-3 Recall | F1 |
| --- | ---: | ---: | ---: | ---: |
| `bluegill` | 68.42% | 54.17% | 91.67% | 60.47% |
| `channel-catfish` | 55.56% | 62.50% | 79.17% | 58.82% |
| `largemouth-bass` | 48.28% | 58.33% | 91.67% | 52.83% |
| `rainbow-trout` | 70.83% | 70.83% | 79.17% | 70.83% |
| `red-drum` | 51.61% | 66.67% | 100.00% | 58.18% |
| `red-snapper` | 86.36% | 79.17% | 87.50% | 82.61% |
| `smallmouth-bass` | 45.00% | 37.50% | 66.67% | 40.91% |
| `spotted-bass` | 45.00% | 37.50% | 75.00% | 40.91% |

## Lookalike Group Metrics

- `black-bass`: 44.44% top-1, 77.78% top-3.
- `red-coastal`: 72.92% top-1, 93.75% top-3.
- `trout-salmonid`: 70.83% top-1, 79.17% top-3.
- `catfish`: 62.50% top-1, 79.17% top-3.
- `lepomis-sunfish`: 54.17% top-1, 91.67% top-3.

## Current Status

Dataset download, split creation, dataset validation, Create ML training, saved-model prediction, and evaluator metrics are complete.

## Abstention Sanity Baseline

The trivial all-abstain baseline was run to verify the U.S. split works with the evaluator:

```bash
python3 ml/scripts/write_abstention_baseline.py \
  ml/data/classification/inaturalist_na_v1/test.manifest.jsonl \
  ml/runs/current_app/inaturalist_na_v1/abstention_predictions.jsonl

python3 ml/scripts/evaluate_predictions.py \
  ml/data/classification/inaturalist_na_v1/test.manifest.jsonl \
  ml/runs/current_app/inaturalist_na_v1/abstention_predictions.jsonl \
  --prior-json ml/angler_priority_v1.json \
  --prior-region north-america
```

Metrics:

- Test examples: 192.
- Prior coverage evaluated: 100%.
- Coverage: 0.00%.
- Top-1 accuracy: 0.00%.
- Top-3 accuracy: 0.00%.
- Macro recall: 0.00%.
- North America angler-priority weighted top-1: 0.00%.
- North America angler-priority weighted top-3: 0.00%.

## Interpretation Notes

This baseline does not meet MVP requirements. It is useful because it proves the full North America train/eval/test path now works and gives us concrete failure modes.

Primary issues:

- Black bass species separation is weak: `smallmouth-bass` and `spotted-bass` are both 37.50% recall, and the black-bass group is only 44.44% top-1.
- Calibration is poor: ECE is 21.28%, so raw confidence is not yet trustworthy.
- High-confidence abstention improves selective accuracy, but even at threshold `0.90`, selective top-1 is only 79.76% with 43.75% coverage.
- Red coastal species are comparatively stronger, especially `red-snapper`.
- Top-3 is much better than top-1, which suggests the app should show alternatives and request context for lookalikes rather than presenting one hard answer.

This dataset is useful for the first U.S. baseline, but it is not a gold benchmark. It uses public observation photos, so the model may learn photographer/source cues and may not fully represent fresh catch-photo UX.

The next U.S. benchmark should add held-out, expert-reviewed catch photos for the majority species: largemouth bass, bluegill, channel catfish, rainbow trout, smallmouth bass, red drum, red snapper, and spotted bass.
