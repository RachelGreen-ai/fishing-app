# iOS Fish Identification ML Training Plan

## Goal

Train an on-device fish species classifier for the iOS app and export it as `FishSpeciesClassifier.mlmodel`. The current app can already load that model dynamically through `FishImageClassifier` when the compiled model is bundled.

## Current State

- The native app does not yet include a trained fish image model.
- `InferenceService` is a calibrated evidence scorer using traits, GPS range, date/time, water type, and habitat.
- `FishImageClassifier` is the new Core ML/Vision boundary. It expects a bundled model named `FishSpeciesClassifier.mlmodel`.

## Target Architecture

1. Image classifier predicts top species from the photo.
2. Evidence scorer reranks or gates predictions using range, season, water type, and habitat.
3. App abstains when the image model is uncertain or context strongly conflicts.
4. User correction feeds a review dataset, not silent automatic retraining.

## Data Strategy

Start with a compact, high-quality North America angler MVP instead of worldwide fish coverage.

Initial species set:

- Largemouth Bass
- Smallmouth Bass
- Spotted Bass
- Bluegill
- Rainbow Trout
- Channel Catfish
- Red Drum
- Red Snapper

Data requirements per species:

- Minimum training floor: 500 usable images per species.
- Better target: 2,000+ images per species.
- Validation and test sets must be held out by source or waterbody when possible.
- Include real catch photos: hands, decks, nets, wet fish, shadows, motion blur, and partial occlusion.
- Remove duplicate images and near-duplicates before splitting.
- Do not use location or season as a label shortcut during image training.

Useful public starting points:

- Fishial.AI open fish recognition work and model scripts: https://github.com/fishial/fish-identification
- Fishial leverage notes for our roadmap: `docs/ml-fishial-leverage.md`
- Fishial.AI dataset/model project overview: https://www.fishial.ai/
- iNaturalist 2021 for broad taxonomic pretraining or fish subset extraction: https://www.tensorflow.org/datasets/catalog/i_naturalist2021
- USGS annotated freshwater fish imagery for a small, clean evaluation baseline: https://www.usgs.gov/data/annotated-fish-imagery-data-individual-and-species-recognition-deep-learning
- Apple Create ML image classifier workflow for Core ML export: https://developer.apple.com/documentation/createml/creating-an-image-classifier-model
- Apple Vision/Core ML image classification integration pattern: https://developer.apple.com/documentation/coreml/classifying-images-with-vision-and-core-ml

## Dataset Layout

Use folder labels for Create ML and a manifest for reproducible training.

```text
ml/data/fish_species_v1/
  train/
    largemouth-bass/
    smallmouth-bass/
  validation/
    largemouth-bass/
    smallmouth-bass/
  test/
    largemouth-bass/
    smallmouth-bass/
  manifest.jsonl
```

Each manifest row should include:

```json
{"image":"train/largemouth-bass/img_001.jpg","label":"largemouth-bass","scientific_name":"Micropterus salmoides","source":"user-review","license":"internal-consent","split":"train","region":"southeast","water_type":"freshwater"}
```

## Training Path

Phase 1: Create ML baseline

- Use folder-per-class data.
- Train an image classifier with Image Feature Print V2 for iOS 17.
- Enable crop, rotate, expose, blur, and noise augmentations.
- Export `FishSpeciesClassifier.mlmodel`.
- Bundle it in `ios/FishingApp` and regenerate the Xcode project.

Phase 2: Stronger PyTorch/Core ML model

- Fine-tune an efficient backbone such as ConvNeXt Tiny, MobileViT, or EfficientNetV2.
- Add class-balanced sampling and label smoothing.
- Export through `coremltools` to image-input Core ML.
- Quantize only after measuring accuracy and calibration loss.

Phase 3: Detection plus classification

- Add a fish detector or segmenter before classification.
- Crop to the fish body so hands, boat decks, and backgrounds do not dominate predictions.
- Keep whole-image fallback for tiny or partial fish.

## Evaluation Gates

Do not ship a model just because validation accuracy looks good.

Required gates for MVP:

- Top-1 accuracy: 85%+ on held-out test.
- Top-3 accuracy: 95%+ on held-out test.
- Per-species recall: 75%+ for every shipped class.
- Abstention: uncertain images should fall below the app's confirmation threshold.
- Confusion review: inspect bass-vs-bass, sunfish-vs-sunfish, trout-vs-salmonid, red drum-vs-snapper-like failures.
- Device latency: under 500 ms on recent iPhones for one photo.
- App size: acceptable after model compression.

## App Integration Contract

The Core ML model must:

- Be named `FishSpeciesClassifier.mlmodel` before adding to Xcode.
- Return `VNClassificationObservation` labels.
- Use label IDs matching `Species.id` where possible, such as `largemouth-bass`.
- Return calibrated confidence scores that can be thresholded.

The iOS app will:

- Show top image predictions in the Model card.
- Continue showing the evidence scorer and context reasons.
- Require strong image evidence before enabling confident save flows.
