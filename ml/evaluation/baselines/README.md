# Baseline Runs

This folder records benchmark results as models evolve.

## Current App Image-Only Baseline

Status: smoke-test only, because `fish_id_gold_v1` has not been assembled yet.

The current iOS app has no bundled image model, so its honest image-only behavior is abstention. It can use manual visual traits and context, but those are not an image classifier baseline.

Command:

```bash
python3 ml/scripts/write_abstention_baseline.py \
  ml/data/benchmarks/fish_id_gold_v1/manifest.jsonl \
  ml/evaluation/baselines/current_app_image_only.fish_id_gold_v1.predictions.jsonl

python3 ml/scripts/evaluate_predictions.py \
  ml/data/benchmarks/fish_id_gold_v1/manifest.jsonl \
  ml/evaluation/baselines/current_app_image_only.fish_id_gold_v1.predictions.jsonl
```

Smoke-test metrics:

```json
{
  "coverage": 0.0,
  "top1_accuracy": 0.0,
  "top3_accuracy": 0.0,
  "macro_recall": 0.0,
  "unknown_abstention_recall": 1.0
}
```

Interpretation:

- This does not meet MVP classification requirements.
- It is an honest floor for the current app before adding `FishSpeciesClassifier.mlmodel`.
- Real baseline metrics require the frozen `fish_id_gold_v1` benchmark images.

## Next Baselines

Run these on `fish_id_gold_v1` in order:

1. Current app image-only abstention baseline.
2. Apple Create ML baseline.
3. Fishial pretrained classifier baseline.
4. Our first trained `fish_species_v1` Core ML model.

## Detector Baselines

- `yolo11n_detector_noaa_lfiw_v1_smoke.md`: first NOAA-only fish detector smoke run.
- `yolo11n_detector_mix_v1_320_e5.md`: mixed NOAA plus Kaggle large-scale fish detector run, including crop-before-classify checks against the current MobileNetV3Large classifier.
