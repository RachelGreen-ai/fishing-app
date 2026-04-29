# Fish ID Data Enrichment Plan

The next accuracy gains should come from better species-labeled images, not just more epochs. The current North America v2 split is balanced at 280 train / 60 validation / 60 test images per class, which is good for measurement but too small for robust real-world angler photos.

## What To Add First

1. More iNaturalist images for weak and high-priority classes:
   - `largemouth-bass`
   - `smallmouth-bass`
   - `spotted-bass`
   - `rainbow-trout`
   - `channel-catfish`

2. Angler-style, species-labeled datasets:
   - AFFiNe has 7,000+ angler fish photos across 30 Netherlands freshwater species, folder-per-species classification labels, and YOLO files per image.
   - This is most useful for Europe coverage and for teaching the model real catch-photo composition.

3. Detection-only fish datasets for preprocessing, not species ID:
   - Roboflow fish detection v11 has 1,876 object-detection images and YOLO26 export support.
   - LILA Community Fish Detection Dataset has >1.9M images/frames and >935k fish boxes from around 17 datasets, but harmonizes annotations to a single `fish` category.
   - NOAA Labeled Fishes in the Wild provides fish boxes in unconstrained underwater imagery, useful for no-fish rejection, crop training, and robustness.

## How To Use Detection Data

Detection datasets should train a fish-localization model:

1. Detect the fish in the camera/photo frame.
2. Crop around the fish with margin.
3. Feed the crop into MobileNetV3Large species classification.
4. Use the box or mask for future length/size estimation.

Do not mix generic `fish` detection labels into the species classifier as species labels.

## Enrichment Rules

- Keep the gold test set frozen.
- Add new data only to train/validation first.
- Track source and license per image.
- Deduplicate by perceptual hash before splitting.
- Split by source/location/user when metadata exists to avoid near-duplicate leakage.
- Preserve the label hierarchy: species, genus, family, common aliases, region.
- Add hard-negative/no-fish images for capture UX, but evaluate them separately as abstention/no-fish detection.

## Next Target

Build `inaturalist_na_v3` with at least 800 train images for the high-priority weak classes and 400+ for the remaining classes. Keep `inaturalist_na_v2` frozen as the current benchmark until v3 has a documented split and baseline.

## Sources

- Fishial external dataset registry: https://docs.fishial.ai/otherprojects/externalfishdatasets
- Roboflow fish detection v11: https://universe.roboflow.com/fish-detection-d7azy/fish-dataset-8ulfi/dataset/11
- LILA Community Fish Detection Dataset: https://lila.science/datasets/community-fish-detection-dataset/
- NOAA Labeled Fishes in the Wild: https://www.fisheries.noaa.gov/west-coast/science-data/labeled-fishes-wild
