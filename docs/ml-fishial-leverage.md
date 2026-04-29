# Fishial Leverage For Fish Identification

Fishial's public `fish-identification` repository is worth using as a reference point and possible pretrained-model source, but its headline accuracy should not be treated as directly comparable to our app benchmark.

## What Fishial Claims

The Fishial README reports:

- Classification model: DinoV2 + ViT.
- Classes: 866.
- Accuracy: 93.22%.
- Latest classifier artifact: DinoV2-224 + ViT pooling, 3-head, subcenter, embedding size 768, TorchScript.
- Other available classifier artifacts: BEiTv2, ConvNeXt Tiny, and older ResNet18 packs.
- Detector and segmentation artifacts are also published as TorchScript.

This is promising, but the README does not define the evaluation split, test-image source distribution, per-species recall, abstention behavior, calibration, or mobile/Core ML performance for that 93.22% number. We should validate it on our own U.S. and Europe splits before adopting it.

## What We Can Reuse

### 1. Stronger Backbone Direction

Our Create ML baselines are useful but weak:

- North America iNaturalist v1: 58.33% top-1, 83.85% top-3.
- Europe archive v1: 57.25% top-1, 78.53% top-3.

Fishial's current direction suggests we should move from Create ML's default classifier to a PyTorch transfer-learning path:

- DinoV2 or BEiTv2/ViT-style backbone for feature extraction.
- Smaller deployment candidate: ConvNeXt Tiny or MobileViT/EfficientNet if Core ML size/latency is too high.
- Export through TorchScript/ONNX/Core ML after evaluation.

### 2. Embedding Model, Not Only Softmax

Fishial's repo includes embedding-oriented classification utilities and metric-learning training scripts. This is especially relevant for our hardest failures:

- `smallmouth-bass` vs `spotted-bass` vs `largemouth-bass`.
- `roach` / `rudd` / `bream`.
- `perch` / `ruffe` / `zander`.

The next model should evaluate an embedding head alongside a classification head. The app can then use nearest-neighbor or centroid distance as a second confidence signal for lookalikes.

### 3. Balanced Batch Sampling

Fishial's triplet training path uses an `MPerClassSampler` style batch sampler. That fits our imbalance policy:

- Keep multiple examples per class in every batch.
- Prevent common species from dominating gradient updates.
- Make metric loss useful for lookalike separation.

### 4. Fish-First Detection/Cropping

Fishial publishes detector and segmentation artifacts. We should evaluate a two-stage pipeline:

1. Detect/crop fish from photo.
2. Classify the fish crop.

This should reduce background leakage from public datasets and improve catch-photo UX. It also supports future size/length workflows.

### 5. Taxonomy And Label Coverage

Fishial's latest label file includes many species that overlap our roadmap:

- North America examples: `Ictalurus punctatus`, `Lepomis macrochirus`, `Lutjanus campechanus`, `Micropterus dolomieu`, `Micropterus punctulatus`, `Oncorhynchus mykiss`, and `Sciaenops ocellatus`.
- Europe examples: `Esox lucius`, `Gadus morhua`, `Gobio gobio`, `Gasterosteus aculeatus`, `Perca fluviatilis`, `Pleuronectes platessa`, `Rutilus rutilus`, `Salmo salar`, `Salmo trutta`, `Sander lucioperca`, `Scardinius erythrophthalmus`, and many marine/coastal classes.

We should add a label-overlap check before evaluating Fishial models so we can map scientific names to our app species IDs.

Important taxonomy caveat: our `largemouth-bass` label currently uses `Micropterus salmoides`, while Fishial's latest labels include `Micropterus nigricans`. Recent taxonomy sources may treat largemouth bass naming differently, so this needs an explicit alias decision before scoring.

## Validation Plan

Do not replace our model just because Fishial reports 93.22%. Validate in this order:

1. Download the latest Fishial classifier TorchScript artifact into ignored `ml/artifacts/fishial/`.
2. Export or wrap inference so it emits our prediction JSONL format.
3. Map Fishial scientific-name labels to our `species_id` labels.
4. Evaluate on:
   - `ml/data/classification/inaturalist_na_v1/test.manifest.jsonl`
   - `ml/data/classification/europe_archive_v1/test.manifest.jsonl`
5. Report:
   - top-1, top-3, macro recall
   - angler-priority weighted accuracy
   - lookalike-group metrics
   - ECE / confidence behavior
   - latency and model size
6. Only after that, decide whether to:
   - use Fishial directly,
   - fine-tune Fishial-style backbones on our labels,
   - use Fishial detector/cropper with our classifier,
   - or distill a smaller on-device model.

## Recommended Next Experiments

### Experiment A: Fishial Zero-Shot Baseline

Use the released Fishial classifier as-is, map overlapping labels, and score it on our test splits. This tells us whether Fishial generalizes to our current app datasets.

Success threshold:

- Beat Create ML by at least 15 top-1 points on U.S. and Europe.
- Improve black-bass and roach/rudd/bream lookalike groups.
- Keep p95 local inference latency within mobile feasibility after conversion planning.

### Experiment B: Fish Crop Then Current Classifier

Use Fishial detector/segmentation or our NOAA-trained detector path to crop fish before classification. Re-run the current Create ML classifier on cropped test images if feasible.

Success threshold:

- Improve black-bass top-1 and calibration without hurting red-snapper/red-drum.

### Experiment C: PyTorch Fine-Tune

Train a small but stronger model with Fishial-inspired choices:

- Backbone: ConvNeXt Tiny first, DinoV2 small/base if feasible.
- Heads: classification plus embedding.
- Sampling: balanced batches.
- Loss: cross-entropy plus supervised contrastive/triplet component.
- Augmentation: horizontal flip, autocontrast/color jitter, random erasing, random crop/pad.
- Export target: Core ML.

Success threshold:

- North America top-1 >= 75% on seed test before gold benchmark work.
- Black-bass top-1 >= 65%.
- Weighted top-3 >= 92%.

## Risks

- Fishial artifacts are TorchScript, not Core ML, so mobile integration requires conversion and latency testing.
- DinoV2/ViT may be too large for first on-device MVP unless distilled or moved server-side.
- The 93.22% metric may use an easier or source-overlapping split.
- Public observation datasets can leak background/source cues; a detector/cropper helps but does not replace a gold benchmark.
- DINOv2 upstream weights may have non-commercial license constraints depending on which weights are used; verify the exact artifact/license before product use.

## Sources

- Fishial repository: https://github.com/fishial/fish-identification
- Fishial model README section: https://github.com/fishial/fish-identification#model-performance
- Fishial latest labels: https://github.com/fishial/fish-identification/blob/main/labels.json
- Fishial docs AI models FAQ: https://docs.fishial.ai/faqs/ai%20models
- DINOv2 model card: https://github.com/facebookresearch/dinov2/blob/main/MODEL_CARD.md
