# ML Label Hierarchy

Fish identification should not be treated as a flat list of labels. The app needs hierarchy so evaluation can distinguish a harmless family-level confusion from a high-risk species-level miss.

## Files

- `ml/label_taxonomy.schema.json`: required taxonomy fields and allowed values.
- `ml/fish_species_v1.taxonomy.json`: North America MVP taxonomy.
- `ml/fish_species_europe_v1.taxonomy.json`: Europe taxonomy.
- `ml/scripts/validate_label_taxonomy.py`: validation script.

## Hierarchy Levels

- `app_regions`: product routing region, such as `north-america` or `europe`.
- `water_types`: freshwater, brackish, saltwater.
- `family` and `family_common`: biological grouping.
- `label_group`: model/evaluation group, often family-like but product-oriented.
- `lookalike_group`: confusion-risk group for failure analysis.
- `taxon_rank`: species, family, or another taxonomic rank.

## Training Rule

Prefer species-level labels for classifiers. Aggregate labels are allowed only when source data cannot reliably provide species labels, such as `sturgeon` mapped to `Acipenseridae` in the Europe archive.

## Evaluation Rule

Report all of the following:

- Top-1 and top-3 species accuracy.
- Macro recall by species.
- Accuracy by `label_group`.
- Accuracy inside `lookalike_group`.
- Abstention performance for unknown/out-of-scope fish.

This prevents a model from looking good overall while failing where anglers care most: confusing visually similar species with different regulations.

