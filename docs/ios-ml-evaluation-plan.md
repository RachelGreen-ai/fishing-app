# Fish Identification Evaluation Plan

## Principle

Do not train first. Build the benchmark first, freeze it, run public baselines, then train only when the benchmark tells us what improved.

The app should optimize for angler trust:

- Correct top species when the image is clear.
- Good top-3 suggestions for lookalikes.
- Honest abstention when the photo or context is weak.
- Fast on-device inference.
- Useful length and weight estimates with uncertainty, not fake precision.

## Golden Benchmark Dataset

Create a private, versioned benchmark named `fish_id_gold_v1`.

It should never be used for training or hyperparameter selection.

Target composition for the first 8 app species:

- 200 images per species minimum.
- 400 images per species preferred.
- At least 25% difficult field images per species.
- At least 20% lookalike pairs, especially black bass and red saltwater species.
- At least 15% low-quality but realistic catch photos.
- At least 10% out-of-scope or unknown fish to test abstention.

Required scenarios:

- Full side profile.
- Angled body.
- Fish in hand.
- Fish on deck/grass/cooler.
- Fish in net.
- Poor light.
- Motion blur.
- Partial fish.
- Multiple fish in frame.
- Juvenile or unusual coloration.

The benchmark must include images from sources, locations, and waterbodies that are not duplicated in training data.

## Manifest Format

Use JSONL so the benchmark can grow while staying reviewable.

```json
{"image_id":"gold_000001","image":"images/gold_000001.jpg","species_id":"largemouth-bass","scientific_name":"Micropterus salmoides","split":"gold","scenario_tags":["hand","angled","field"],"region":"southeast","water_type":"freshwater","quality":"medium","source":"expert-labeled","license":"internal-eval-only"}
```

For abstention examples:

```json
{"image_id":"gold_009001","image":"images/gold_009001.jpg","species_id":"unknown","scientific_name":"","split":"gold","scenario_tags":["out-of-scope"],"region":"west","water_type":"freshwater","quality":"medium","source":"expert-labeled","license":"internal-eval-only"}
```

## Baseline Models

Run these before training our own model:

1. Current native evidence scorer.
   - Purpose: quantify the current app floor.
   - Expected: poor image-only accuracy, useful abstention/context behavior.
2. Apple Create ML image classifier.
   - Purpose: quick on-device Core ML baseline.
   - Uses folder-per-class images and exports directly to `.mlmodel`.
3. Fishial pretrained models.
   - Purpose: strong public fish-specific baseline.
   - Fishial publishes detection, segmentation, and classification models/training scripts, including classification models over hundreds of fish classes.
4. General vision embeddings plus lightweight classifier.
   - Purpose: cheap non-fish-specific baseline.
   - Useful for testing whether domain-specific fish data is doing real work.

## Classification Metrics

Primary gates:

- Top-1 accuracy.
- Top-3 accuracy.
- Macro recall.
- Per-species precision, recall, and F1.
- Lookalike-group accuracy.
- Unknown/out-of-scope abstention recall.
- Selective accuracy at coverage levels: 50%, 70%, 90%.

Calibration and product metrics:

- Expected calibration error.
- High-confidence error rate.
- Mean reciprocal rank.
- Median and p95 inference latency.
- App size impact.
- Battery/thermal behavior on device.

## Pass Criteria For MVP

For `fish_id_gold_v1`:

- Top-1 accuracy >= 85%.
- Top-3 accuracy >= 95%.
- Macro recall >= 80%.
- No species recall below 70%.
- Lookalike-group top-1 >= 75%.
- Unknown abstention recall >= 85%.
- High-confidence error rate below 3% for predictions above 90% confidence.
- p95 iPhone inference latency below 800 ms.

## Size And Weight Estimation

Fish size cannot be reliably inferred from a single unconstrained photo without scale. The app should support size estimation only when at least one scale signal is present:

- ARKit measurement flow.
- LiDAR/depth on supported devices.
- Known reference object, such as a measuring board, lure, coin, or card.
- User-marked nose and tail points on a fish lying flat beside a reference.

Length metrics:

- Total length MAE in cm.
- Total length MAPE.
- Percentage within 1 cm, 2 cm, and 5 cm.
- Failure rate when no valid scale exists.

Weight metrics:

- Weight MAE in grams.
- Weight MAPE.
- Species-specific error buckets.
- Confidence interval coverage.

Weight estimate formula:

```text
W = a * L^b
```

Use species-specific length-weight parameters where available, and show uncertainty because condition, sex, season, gut fullness, and regional population differences affect weight.

## Size Benchmark Manifest Extension

```json
{"image_id":"gold_size_000001","image":"images/gold_size_000001.jpg","species_id":"largemouth-bass","measured_total_length_cm":42.3,"measured_weight_g":1180,"reference_object":"measuring-board","reference_length_cm":50.0,"view":"side-flat","scale_quality":"high"}
```

## Iteration Loop

1. Freeze `fish_id_gold_v1`.
2. Run current evidence scorer.
3. Run Create ML baseline.
4. Run Fishial baseline where label overlap allows.
5. Train `fish_species_v1`.
6. Evaluate and inspect failure cases.
7. Add training data only for failure modes, not benchmark images.
8. Release only if the new model improves primary metrics and does not worsen abstention or lookalikes.

## References

- Dataset registry and Europe source ranking: `docs/datasets/fish-dataset-registry.md`
- Apple Create ML image classifier workflow: https://developer.apple.com/documentation/createml/creating-an-image-classifier-model
- Apple Vision and Core ML image classification sample: https://developer.apple.com/documentation/coreml/classifying-images-with-vision-and-core-ml
- Fishial public training scripts and pretrained fish models: https://github.com/fishial/fish-identification
- Fishial project/model overview: https://www.fishial.ai/
- USGS annotated fish imagery dataset: https://www.usgs.gov/data/annotated-fish-imagery-data-individual-and-species-recognition-deep-learning
- iNaturalist 2021 dataset: https://www.tensorflow.org/datasets/catalog/i_naturalist2021
- FishBase length-weight relationship notes: https://fishbase.org/FishOnLine/English/FOL_BiodiversityAndMorphology.htm
- Apple Measure app support note on approximate AR measurements: https://support.apple.com/en-la/102468
