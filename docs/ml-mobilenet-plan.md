# MobileNet Model Plan

We are moving beyond the Create ML baseline to a controlled MobileNet-family transfer-learning baseline.

## Why MobileNet

MobileNet is designed for efficient mobile vision. The older `hollance/MobileNet-CoreML` project demonstrates the same core idea for iOS/Core ML: a compact convolutional model running directly on device. For our app, the modern equivalent is to train a Keras MobileNetV2 or MobileNetV3 model on our fish labels and export it to Core ML.

## Candidate Models

Use this order:

1. `MobileNetV3Small`: first on-device candidate; compact and fast.
2. `MobileNetV3Large`: still mobile-oriented, likely more accurate.
3. `MobileNetV2`: useful comparison and commonly supported by conversion examples.

Keras documents MobileNetV3Small as a small architecture with about 2.9M parameters for the 1.0/224 checkpoint, while MobileNetV3Large is about 5.4M parameters. MobileNetV3 includes preprocessing in the model by default, which simplifies Core ML export.

## Implementation

Scripts:

- `ml/scripts/train_keras_mobilenet_classifier.py`
- `ml/scripts/predict_keras_classifier.py`

Dependencies:

```bash
/Users/junyishen/.local/bin/uv venv ml/.venv-mobilenet --python /opt/homebrew/bin/python3.11
/Users/junyishen/.local/bin/uv pip install --python ml/.venv-mobilenet/bin/python -r ml/requirements-mobilenet.txt
```

Training command:

```bash
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

The Core ML export from this script writes `FishSpeciesClassifier.mlpackage`. Core ML Tools 7+ defaults to the ML Program format for modern deployment targets, and Apple documents `.mlpackage` as the save format for ML Programs.

If the environment cannot download ImageNet weights, use `--weights none` only as a pipeline smoke test. The real model-quality comparison should use ImageNet initialization.

Prediction and evaluation:

```bash
ml/.venv-mobilenet/bin/python ml/scripts/predict_keras_classifier.py \
  ml/artifacts/keras/mobilenet_v3_small_na_v2/final.keras \
  ml/artifacts/keras/mobilenet_v3_small_na_v2/labels.json \
  ml/data/classification/inaturalist_na_v2/test.manifest.jsonl \
  ml/data/classification/inaturalist_na_v2 \
  ml/runs/keras/mobilenet_v3_small_na_v2/test_predictions.jsonl

python3 ml/scripts/evaluate_predictions.py \
  ml/data/classification/inaturalist_na_v2/test.manifest.jsonl \
  ml/runs/keras/mobilenet_v3_small_na_v2/test_predictions.jsonl \
  --prior-json ml/angler_priority_v1.json \
  --prior-region north-america
```

## Baseline To Beat

Current North America Create ML baselines:

- v1 Create ML: 58.33% top-1, 83.85% top-3.
- v2 Create ML 100 iterations: 62.92% top-1, 87.08% top-3.
- v2 hierarchical black-bass rerank: 66.25% top-1, 83.96% top-3.

MobileNetV3Large is the current best app candidate.

| Model | Eval setup | Top-1 | Top-3 | Weighted top-1 | ECE | Notes |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| MobileNetV3Small | bilinear evaluator | 65.00% | 89.58% | 61.12% | 2.63% | Compact but under the target quality bar. |
| MobileNetV2 | bilinear evaluator | 65.62% | 91.46% | 62.32% | 7.34% | Compatibility baseline; slower in local CPU eval. |
| MobileNetV3Large | bilinear evaluator | 71.46% | 91.46% | 67.23% | 4.10% | First useful general model lift. |
| MobileNetV3Large | bilinear + horizontal flip TTA | 72.71% | 92.50% | 68.38% | 3.14% | Better app-side inference setting if latency is acceptable. |
| MobileNetV3Large weighted/smoothed | bilinear evaluator | 73.33% | 92.92% | 70.92% | 3.35% | Uses North America angler-priority class weights and label smoothing. |
| MobileNetV3Large weighted/smoothed | bilinear + horizontal flip TTA | 73.75% | 93.75% | 71.95% | 4.94% | Current best accuracy; validate on a larger gold set before shipping. |

Weighted/smoothed training command:

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

## Current Blocker

The MobileNet environment has been created and dependencies installed under ignored `ml/.venv-mobilenet/`. The first training run reached the ImageNet weight download, but the Codex app escalation gate rejected the networked rerun because the session usage limit was hit. Run the training command above from a normal terminal, or retry after the gate resets.

## Sources

- MobileNet-CoreML reference: https://github.com/hollance/mobilenet-coreml
- Keras MobileNet docs: https://keras.io/api/applications/mobilenet/
- Core ML Tools ML Program guide: https://apple.github.io/coremltools/docs-guides/source/convert-to-ml-program.html
