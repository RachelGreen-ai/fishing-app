# Catch ID

Phase 1 prototype for the fish identification plan in `fishing-app-plan.md`.

## Run

```bash
npm run dev
```

Open `http://127.0.0.1:4173`.

## What Is Built

- Guided photo intake with client-side quality checks for resolution, lighting, contrast, and sharpness.
- Context capture for region, water type, habitat, date, and waterbody.
- Visual trait capture for body shape, mouth, markings, tail/fin, and color.
- Local inference orchestrator with species scoring, location/date/habitat priors, top alternatives, confidence tiers, and cautious harvest language.
- Correction flow and local review queue for active-learning style feedback.
- Local catch log for confirmed or corrected IDs.

## Identification Model Boundary

The current classifier is a deterministic prototype in `src/inference.js`. It is intentionally honest about uncertainty and should not be treated as a real computer-vision model.

The production path from the plan should replace or augment this boundary:

1. Keep `identifyFish(evidence)` as the UI contract.
2. Add a backend scan session endpoint for upload, result retrieval, and feedback.
3. Route primary inference to Fishial.ai or another fish-specific API.
4. Preserve the local scoring concepts as calibration inputs: photo quality, location/date/habitat priors, lookalike groups, and abstention.
5. Store corrections and uncertain scans for review and future proprietary training data.

## Next Steps

1. Add real upload sessions and API response mocks that match the future backend contract.
2. Integrate a fish-ID vendor behind an environment-configured service.
3. Expand the species catalog with canonical taxonomy, synonyms, protected/invasive flags, and regional coverage.
4. Add consent and image-retention controls before storing user photos.
5. Build an admin review queue for uncertain IDs, corrections, rare species, and lookalike disagreements.
