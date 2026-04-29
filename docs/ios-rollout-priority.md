# iOS Rollout Priority

The fastest path to a credible first iOS build is to ship a simple, honest on-device identification loop and keep richer data work behind measured gates.

## Priority 1: Hybrid Identification Loop

Status: started.

- Use Core ML image predictions when a bundled model exists.
- Apply conservative geo-seasonal priors from GPS/date/water context.
- Keep manual traits optional as rescue evidence.
- Explain why the app ranked a species.

## Priority 2: Bundle The Best Model

Current candidate:

- MobileNetV3Large weighted/smoothed.
- Best measured setting: bilinear + horizontal flip TTA.
- Benchmark: 73.75% top-1, 93.75% top-3, 71.95% North America angler-weighted top-1.

Implementation:

1. Export `FishSpeciesClassifier.mlpackage`.
2. Add it to the iOS target.
3. Verify labels match `SpeciesCatalog.id`.
4. Measure on-device latency and memory.
5. Decide whether flip TTA is always-on, user-gated, or only used when confidence is close.

## Priority 3: California/Washington Local Priors

Start lightweight:

- California: CDFW PISCES HUC12 native species and CDFW fish planting/stocking signals.
- Washington: WDFW SalmonScape salmonid distribution and stocking reports.

Implementation:

1. Create compact offline JSON bundles.
2. Map GPS to broad state/region first, then HUC/waterbody later.
3. Rerank, never hard-filter.
4. Build `geo_gold_v1` before enabling by default.

## Priority 4: Detection And Crop Assist

Use YOLO26/fish detection data for:

- fish-in-frame checks,
- crop-before-classify,
- no-fish rejection,
- future size/length estimation.

Do not mix generic fish detection labels into species classification.

## Priority 5: Data Enrichment

Improve species classifier data after the app loop is working:

- Add more iNaturalist/catch-photo data for weak priority classes.
- Build `inaturalist_na_v3`.
- Keep the current v2 benchmark frozen until v3 is documented.
