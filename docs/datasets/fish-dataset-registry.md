# Fish Dataset Registry

This registry tracks useful public datasets for the fishing app. Datasets are grouped by likely app use, not by academic importance alone.

## Priority Sources

### AFFiNe - Angling Freshwater Fish Netherlands

- Source: https://www.kaggle.com/datasets/jorritvenema/affine
- Listed by Fishial external dataset docs: https://docs.fishial.ai/otherprojects/externalfishdatasets
- Region: Europe, Netherlands.
- Best use: European angler-photo classification seed and evaluation candidate.
- Coverage noted by Fishial: 7,000+ images, 30 freshwater species, 100-500 images per species, folder-per-species classification format, YOLO file per image.
- License note: Fishial says non-commercial use is permitted.
- App fit: High, because photos are from anglers and freshwater species overlap a recreational fishing use case.

### QUT FISH / Kaggle Fish Species Image Data

- Source: https://www.kaggle.com/datasets/sripaadsrinivasan/fish-species-image-data
- Region: mixed/global.
- Best use: public seed source for controlled, cropped, out-of-water, and in-situ fish appearances.
- Coverage noted by Kaggle: about 3,960 images, 468 fish species.
- License: CC BY-SA 3.0.
- App fit: Medium. Useful for broad fish morphology, but overlap with our MVP labels must be measured after import.
- Local importer: `ml/scripts/prepare_qut_kaggle_seed.py`

### PomerFish

- Source: https://www.nature.com/articles/s41597-025-06393-8
- Data repository noted in paper: https://zenodo.org/records/17432128
- Region: Central Europe, Pomerania region, Germany/Poland freshwater systems.
- Best use: European freshwater detection/segmentation, habitat-realistic underwater model evaluation, size/growth research direction.
- Coverage noted by paper: PomerFishObj has 14,989 high-resolution images with bounding boxes and 3,273 negative samples; PomerFishSeg has 1,115 images with polygon segmentation masks/negative samples.
- License noted by paper: CC BY 4.0.
- App fit: High for Europe detection/segmentation and future size estimation, medium for angler photo classification.

### Deep Vision Fish Dataset

- Source: https://metadata.nmdc.no/metadata-api/landingpage/01d102345aef4639f063a13ea20cd3f3
- Region: Norway / Northeast Atlantic survey data.
- Best use: European/North Atlantic pelagic species classification baseline.
- Species noted by NMDC/LILA: blue whiting, Atlantic herring, mesopelagic fishes, Atlantic mackerel.
- License noted by NMDC: CC BY 4.0.
- App fit: Medium for marine Europe species; lower for freshwater angler use.

### Community Fish Detection Dataset - LILA

- Source: https://lila.science/datasets/community-fish-detection-dataset/
- Region: mixed/global; includes several Europe-relevant subsets.
- Best use: fish detector pretraining, negative/empty handling, and bounding-box detection robustness.
- Format: harmonized COCO archive with a single category, `fish`.
- License: per-source; LILA notes most are permissive, but some include non-commercial restrictions.
- Useful Europe-relevant subsets:
  - Brackish Denmark videos: 89 short videos and about 14,764 extracted frames, CC BY-SA 4.0.
  - Deep Vision Fish Dataset: blue whiting, Atlantic herring, mesopelagic fishes, Atlantic mackerel, CC BY 4.0.
  - FishCLEF-2015: species-level boxes over underwater videos; license not explicitly stated by LILA.
- App fit: High for fish/not-fish detection; not sufficient alone for species classification because the harmonized archive has one `fish` category.

### FishCLEF 2015

- Source: https://www.imageclef.org/lifeclef/2015/fish
- Zenodo mirror: https://zenodo.org/records/15202605
- Region: tropical reef imagery, not European recreational fishing.
- Best use: species-level underwater video benchmark and public baseline comparison.
- Coverage noted by ImageCLEF: 20 training videos, 73 test videos, more than 9,000 training annotations, more than 20,000 sample images, 15 fish species.
- App fit: Medium for underwater robustness and evaluator testing; lower for Europe/US angler catch photos.

### NOAA Labeled Fishes in the Wild

- Source: https://www.fisheries.noaa.gov/west-coast/science-data/labeled-fishes-wild
- Region: US West Coast ROV survey imagery.
- Best use: detection benchmark, fish/non-fish negatives, hard underwater scenes.
- Coverage noted by NOAA: dataset archive v1.1 is 423 MB; training positive set has 929 image files with 1,005 marked fish; negative image set includes 3,167 images; test video annotations mark 2,061 fish objects.
- App fit: Medium for detector/abstention training, low for recreational species classification.

### alzayats/fish-datasets

- Source: https://github.com/alzayats/fish-datasets
- Best use: index of historical fish detection/segmentation dataset exports and links.
- Notes from README: standardized fish datasets for deep learning, Roboflow/CVAT exports, YOLOv3/v4 model links, MIT license for repository code.
- App fit: Useful as a source index; individual linked datasets need separate license and label review.

## Practical Source Ranking

For species classification:

1. AFFiNe for Europe angler freshwater photos.
2. QUT FISH for broad visual morphology and public seed experiments.
3. Deep Vision for North Atlantic marine species.
4. FishCLEF for underwater species-video evaluation.

For detection/cropping:

1. LILA Community Fish Detection.
2. PomerFish.
3. NOAA Labeled Fishes in the Wild.
4. alzayats/fish-datasets exports if licenses are acceptable.

For size/weight:

1. PomerFish segmentation track.
2. LILA datasets with boxes/segmentation and stable camera metadata where available.
3. App-collected AR/reference-object photos with measured length/weight.

## Europe Expansion

Use `ml/fish_species_europe_v1.labels.json` as the first European label set. It is intentionally broader than the first US MVP labels and should be narrowed per launch country and dataset coverage after source inspection.

