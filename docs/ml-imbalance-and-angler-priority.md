# ML Imbalance And Angler Priority

Fish identification is an imbalanced deployment problem. We should not train or evaluate as if every species is equally likely to appear in a user's photo.

## Decision

Use two scorecards:

- Balanced quality: macro recall, per-species recall, and lookalike-group metrics.
- Majority-user quality: region-specific angler-priority weighted top-1 and top-3 accuracy.

Both matter. Balanced metrics stop the model from abandoning rare species. Angler-priority metrics make sure we satisfy the fish a catcher is most likely to photograph.

## Initial Priors

The first version lives in `ml/angler_priority_v1.json`.

These priors are intentionally practical, not final truth. They combine official survey evidence, Europe inland fishery references, and the current app taxonomy. We should update them with app telemetry, local fishing-license/catch-report data, creel surveys, and region-specific regulations.

North America starting priority:

- Tier 1: largemouth bass, bluegill, channel catfish, rainbow trout.
- Tier 2: smallmouth bass, red drum, red snapper.
- Tier 3: spotted bass.

Europe starting priority:

- Tier 1: European perch, common carp, northern pike, zander, brown trout, roach, common bream.
- Tier 2: Wels catfish, tench, cod, European seabass, Atlantic salmon, European eel, rudd.
- Tier 3: remaining supported taxonomy labels.

## Training Policy

Do not mirror raw dataset imbalance directly. Public datasets reflect collector behavior, website availability, and source quirks.

For training:

- Use class-balanced or capped sampling so high-volume classes do not dominate every batch.
- Use class-weighted loss or focal loss for long-tail classes once we move beyond Create ML.
- Oversample weak but important lookalike classes with realistic augmentation.
- Keep a minimum data floor for every promoted species.
- Merge or demote labels that are too sparse or too visually ambiguous for reliable species-level release.

For evaluation:

- Keep a balanced diagnostic benchmark.
- Report angler-priority weighted metrics using `--prior-json`.
- Report prior coverage so missing high-value species are visible.
- Never allow weighted metrics to hide low macro recall or regulation-sensitive misses.

## Evidence Notes

The U.S. 2016 National Survey reports black bass, panfish, catfish/bullheads, trout, and crappie among the largest non-Great-Lakes freshwater targets. Great Lakes and saltwater have different leaders, including salmon/walleye/sauger/steelhead in Great Lakes and red drum/striped bass/flatfish/sea trout/bluefish/salmon in saltwater.

Europe is more regional, so the v1 prior uses a broader blend: inland/coarse species such as perch, carp, pike, zander, trout, roach, bream, tench, eel, catfish, chub, and related cyprinids, plus coastal/marine species retained for expansion.

## References

- U.S. Census / U.S. Fish and Wildlife Service, 2016 National Survey: https://www.census.gov/library/publications/2018/demo/fhw-16-nat.html
- 2016 National Survey PDF table excerpts: https://www.census.gov/content/dam/Census/library/publications/2018/demo/fhw16-nat.pdf
- FAO Inland fisheries of Europe: https://www.fao.org/4/t0798e/T0798E17.htm
- FAO Inland fisheries questionnaire summary: https://www.fao.org/fishery/docs/CDrom/aquaculture/a0844t/docrep/009/T0377E/T0377E23.htm
- UK coarse species practical guide: https://tacklebox.co.uk/common-uk-coarse-species-roach-bream-carp-tench-perch-and-more/
