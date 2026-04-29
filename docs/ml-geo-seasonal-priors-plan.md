# Geo-Seasonal Fish Identification Priors

Vision should remain the primary signal, but GPS, watershed, season, salinity, stocking, and regional species lists can improve both accuracy and user trust. The right architecture is a local prior layer that reranks model probabilities without hiding the vision result.

## Product Idea

When the user opens the camera or picks a fish photo:

1. Ask for location permission with a clear reason: better local species suggestions.
2. Convert GPS to state, county, waterbody if available, HUC12 watershed, and rough water type.
3. Build a local species prior from region, watershed, season, stocking, and regulations.
4. Combine the prior with MobileNet/YOLO classifier probabilities.
5. Show the top result plus local context:
   - "Common in this watershed"
   - "Recently stocked nearby"
   - "Rare here; visual match is strong"
   - "Protected species; check regulations"

The app should never hard-block a visually strong species solely because a source says it is absent. Species move, anglers travel, stocked fish exist, and source coverage is uneven. Use a small floor probability for out-of-range species.

## Scoring

Use log-space reranking:

```text
score(species) =
  vision_logit(species)
  + lambda_geo * log(location_prior(species))
  + lambda_season * log(season_prior(species))
  + lambda_water * log(water_type_prior(species))
  + lambda_stocking * log(stocking_prior(species))
```

Start conservative:

- `lambda_geo = 0.25`
- `lambda_season = 0.10`
- `lambda_water = 0.20`
- `lambda_stocking = 0.20`

Evaluate with and without priors. The prior is successful only if top-1, angler-weighted top-1, calibration, and lookalike-group accuracy improve without suppressing valid rare catches.

## Data Schema

Keep this as an offline bundle for iOS:

```json
{
  "schema_version": "1.0",
  "source": "cdfw_pisces_ds1353",
  "region": "california",
  "spatial_unit": "huc12",
  "generated_at": "2026-04-29",
  "species_presence": [
    {
      "species_id": "coastal-rainbow-trout",
      "scientific_name": "Oncorhynchus mykiss",
      "common_names": ["Coastal Rainbow Trout", "Rainbow Trout"],
      "huc12": "180500050101",
      "presence": "extant_range",
      "native_status": "native",
      "confidence": 0.8,
      "seasonality": {
        "jan": 0.7,
        "feb": 0.7,
        "mar": 0.8,
        "apr": 0.9,
        "may": 0.9,
        "jun": 0.8,
        "jul": 0.6,
        "aug": 0.6,
        "sep": 0.6,
        "oct": 0.7,
        "nov": 0.7,
        "dec": 0.7
      },
      "source_url": "https://map.dfg.ca.gov/metadata/ds1353.html"
    }
  ]
}
```

## NOAA Fisheries Species Directory

Source: https://www.fisheries.noaa.gov/species-directory

Useful for:

- Canonical common names and scientific names.
- Aliases and "also known as" names.
- NOAA region tags such as Alaska, West Coast, Southeast, New England/Mid-Atlantic, and Pacific Islands.
- Species category tags such as groundfish, reef fish, highly migratory fish, protected fish, and wild-caught seafood.
- Protected status flags like ESA, MMPA, and CITES where applicable.
- Educational species profile links and official illustrations/photos where available.

Limitations:

- It is not a complete freshwater sportfish range source.
- Its regions are coarse, not watershed-level.
- Many entries are marine/federal-management oriented.
- Images are useful for UI and references, but not enough to train a robust catch-photo model.

Best use:

1. Build a `species_metadata` table.
2. Normalize common names, aliases, scientific names, and NOAA categories.
3. Flag protected/regulated species for UX warnings.
4. Add NOAA profile links to result detail pages.
5. Use NOAA EFH GIS layers for federally managed marine species spatial priors.

## California MVP

California is the strongest first state because CDFW has a watershed-native-fish dataset.

Primary sources:

- California Native Fish Species by Watershed [ds1353], CDFW/PISCES HUC12 dataset.
- Planting Location - CDFW [ds2897], fish planting locations for inland waters.
- CDFW Fish Planting Schedule for recent and upcoming stocked trout signals.
- CDFW Fish Species of Special Concern for protected/sensitive context.

Plan:

1. Download CDFW `ds1353` HUC12 species data.
2. Map PISCES common names to our species IDs and taxonomy.
3. Build a compact HUC12 -> species prior bundle.
4. Add fish planting locations/schedules as a temporary stocking boost for rainbow trout and stocked species.
5. Evaluate against California-tagged iNaturalist/photo test subsets before enabling by default.

## Washington MVP

Washington is a strong second state because WDFW has salmonid distribution and stocking information.

Primary sources:

- WDFW SalmonScape fish distribution data for salmonid species/runs and habitat use.
- WDFW Fish Distributions ArcGIS item for Chinook, steelhead, chum, pink, coho, bull trout, sockeye, kokanee, and use/distribution type.
- WDFW stocking reports and statewide hatchery trout/kokanee plans.
- WDFW regulations pages for season/legal UX context.

Plan:

1. Start with salmonids because the data is strongest.
2. Use distribution type as confidence: documented > presumed > modeled > historic.
3. Use run/season information for salmon and steelhead seasonal priors.
4. Use stocking reports for lake trout/kokanee boosts.
5. Keep native/protected/sensitive species warnings separate from model confidence.

## Other Reliable Sources

- USGS NAS: nonindigenous aquatic species API and occurrence data by state/hydrologic basin. Useful for invasive/non-native species priors.
- NatureServe Explorer API: taxonomy, conservation status, state/province presence, data-sensitivity signals.
- USGS Watershed Boundary Dataset/NHDPlus: HUC boundaries and waterbody context.
- NOAA EFH GIS: marine habitat polygons for federally managed species such as red drum and reef fish.
- State fish and wildlife GIS portals: best source for fine-grained local presence.
- GBIF/iNaturalist: useful for labeled images and occurrence checks, but should be filtered and deduplicated before use as training data.

## Cost And Complexity

Low-cost v0:

- State-level and NOAA-region priors.
- Static JSON bundle.
- No live API calls.
- 1-2 weeks.

Practical v1:

- California HUC12 priors.
- Washington salmonid priors.
- Stocking boosts.
- Offline spatial index.
- 3-5 weeks.

Richer v2:

- More states.
- Waterbody matching.
- Regulations/season UX.
- Species-specific migration/spawn priors.
- Ongoing monthly or quarterly data refresh job.

## Privacy

GPS should be processed on device when possible. The app can ship a compact spatial prior bundle and only send analytics after explicit consent. Location should improve ranking, not require an account or upload.

## Evaluation

Create a `geo_gold_v1` benchmark:

- Images with species labels.
- GPS or at least state/county/waterbody/HUC metadata.
- Date/month.
- Water type.
- Source/license.

Metrics:

- Vision-only top-1/top-3.
- Prior-reranked top-1/top-3.
- Angler-weighted top-1/top-3.
- Lookalike groups.
- Rare-but-valid catch suppression rate.
- Calibration and abstention/no-fish behavior.

Shipping gate:

- Do not enable geo priors by default until they improve weighted top-1 and do not increase rare-valid suppression beyond an agreed threshold.
