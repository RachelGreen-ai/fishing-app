# QUT FISH Kaggle Dataset

Source: https://www.kaggle.com/datasets/sripaadsrinivasan/fish-species-image-data

Use in this project:

- Public seed benchmark candidate.
- Public baseline source for quick model experiments.
- Not final `fish_id_gold_v1` unless a reviewed subset is promoted and frozen.

Dataset notes from Kaggle:

- About 3,960 images.
- 468 fish species.
- Real-world images in controlled, out-of-the-water, and in-situ conditions.
- Includes raw images with background content and cropped images.
- Organized by family/species directories.
- License: CC BY-SA 3.0.

Citation listed by Kaggle:

```text
@inproceedings{anantharajah2014local,
title={Local inter-session variability modelling for object classification},
author={Anantharajah, Kaneswaran and Ge, ZongYuan and McCool, Christopher and Denman, Simon and Fookes, Clinton B and Corke, Peter and Tjondronegoro, Dian W and Sridharan, Sridha},
booktitle={Winter Conference on Applications of Computer Vision (WACV), 2013 IEEE Conference},
year={2014}
}
```

Download:

```bash
kaggle datasets download -d sripaadsrinivasan/fish-species-image-data -p ml/data/sources/qut_fish_kaggle --unzip
```

Then create a seed manifest:

```bash
python3 ml/scripts/prepare_qut_kaggle_seed.py \
  ml/data/sources/qut_fish_kaggle \
  ml/data/benchmarks/qut_fish_seed_v1 \
  --mode manifest-only
```

Inspect `unmatched_species_report.json` after import. The QUT dataset has many species, so we need to confirm overlap with our MVP label set before treating it as useful for species-level baseline metrics.

