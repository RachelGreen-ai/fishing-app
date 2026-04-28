# Local Dataset Source Coverage

Generated from local source drops under `docs/datasets/`. Raw images and archives are intentionally git-ignored.

## QUT FISH / Kaggle Fish_Data

Local path: `docs/datasets/Fish_Data`

Importer:

```bash
python3 ml/scripts/prepare_qut_kaggle_seed.py \
  docs/datasets/Fish_Data \
  ml/data/benchmarks/qut_fish_seed_v1 \
  --mode manifest-only \
  --prefer cropped
```

Result:

- Matched MVP/Europe species: 0.
- Matched images: 0.
- Used `final_all_index.txt`: yes.
- Top unmatched species include `caranx_melampygus`, `oxymonacanthus_longirostris`, `cantherhines_pardalis`, `halichoeres_melanurus`, `lethrinus_nebulosus`, `pseudanthias_squamipinnis`, and several `lutjanus` species.

Interpretation:

- Useful for broad marine morphology experiments.
- Not directly useful for current US freshwater MVP labels or the first Europe freshwater label set.
- Could become useful if we add Indo-Pacific reef/marine species labels.

## AFFiNe / Europe Archive

Local path: `docs/datasets/archive`

Importer:

```bash
python3 ml/scripts/prepare_qut_kaggle_seed.py \
  docs/datasets/archive \
  ml/data/benchmarks/europe_archive_seed_v1 \
  --labels ml/fish_species_europe_v1.labels.json \
  --aliases ml/fish_species_europe_v1.aliases.json \
  --mode manifest-only \
  --prefer any \
  --source-name affine-kaggle \
  --license CC-BY-NC-SA-4.0 \
  --split seed
```

Result:

- Matched images: 7,482.
- Matched species folders: 30.
- Unmatched folders: 0.

Matched species counts:

| Species | Count |
| --- | ---: |
| common-carp | 589 |
| asp | 343 |
| common-barbel | 336 |
| ide | 334 |
| roach | 318 |
| tench | 316 |
| northern-pike | 311 |
| rudd | 311 |
| zander | 302 |
| grass-carp | 293 |
| sturgeon | 293 |
| chub | 282 |
| wels-catfish | 272 |
| common-bream | 271 |
| brown-trout | 270 |
| european-eel | 266 |
| prussian-carp | 259 |
| european-perch | 248 |
| pumpkinseed | 248 |
| round-goby | 244 |
| silver-bream | 244 |
| crucian-carp | 242 |
| ruffe | 236 |
| gudgeon | 228 |
| monkey-goby | 102 |
| bighead-goby | 93 |
| vimba-bream | 71 |
| common-dace | 66 |
| three-spined-stickleback | 58 |
| bitterling | 36 |

Current app image-only abstention baseline on this seed manifest:

- coverage: 0.0
- top1_accuracy: 0.0
- top3_accuracy: 0.0
- macro_recall: 0.0

Interpretation:

- This is our best local source for Europe fish classification work.
- Because the dataset README notes possible citizen-science label noise, use it as seed/training data first.
- Promote a reviewed subset into a true gold benchmark after manual or expert review.

Reproducible training split:

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
```

Split result:

- Trainable labels: 29.
- Skipped labels: `bitterling` only, because it has 36 images and the split floor is 50.
- Train/validation/test folders are written under `ml/data/classification/europe_archive_v1`.
- Matching `labels.json` and `taxonomy.json` subsets are written into the split output.
- Validation command:

```bash
python3 ml/scripts/validate_dataset.py \
  ml/data/classification/europe_archive_v1 \
  ml/data/classification/europe_archive_v1/labels.json \
  --min-train 40 \
  --min-validation 8 \
  --min-test 8
```

## NOAA Labeled Fishes In The Wild

Local path: `docs/datasets/_LABELED-FISHES-IN-THE-WILD`

Importer:

```bash
python3 ml/scripts/prepare_noaa_lfiw_detection_seed.py \
  docs/datasets/_LABELED-FISHES-IN-THE-WILD \
  ml/data/detection/noaa_lfiw_seed_v1 \
  --mode manifest-only
```

Result:

- Manifest rows: 1,473.
- Positive training/validation images: 1,326.
- Positive training/validation boxes: 929.
- Negative seabed images: 147.
- Test video mark rows parsed: 206.

Interpretation:

- Strong detector/abstention source.
- Not a species classifier source.
- Useful for fish/not-fish detection, empty-scene robustness, and underwater hard examples.
