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
- Mock scan-session API for creating scans, retrieving results, and submitting feedback.
- Correction flow and local review queue for active-learning style feedback.
- Local catch log for confirmed or corrected IDs.

## API Contract

The prototype exposes the first backend boundary:

- `POST /api/scans` creates a scan session from photo quality, context, and visual trait evidence.
- `GET /api/scans/:id` retrieves a scan result.
- `POST /api/scans/:id/feedback` records confirmations, alternatives, and manual corrections.

The current API stores scans and feedback in server memory. It is meant to define the shape of the product workflow before adding object storage, signed uploads, a database, and a vendor model.

## Identification Model Boundary

The current classifier is a deterministic prototype in `src/inference.js`, called through the scan-session API in `server.js`. It is intentionally honest about uncertainty and should not be treated as a real computer-vision model.

The production path from the plan should replace or augment this boundary:

1. Keep the `/api/scans` workflow as the UI contract.
2. Add signed upload URLs and image storage to scan creation.
3. Route primary inference to Fishial.ai or another fish-specific API.
4. Preserve the local scoring concepts as calibration inputs: photo quality, location/date/habitat priors, lookalike groups, and abstention.
5. Store corrections and uncertain scans for review and future proprietary training data.

## Next Steps

1. Add real signed upload sessions and object-storage metadata.
2. Integrate a fish-ID vendor behind an environment-configured service.
3. Expand the species catalog with canonical taxonomy, synonyms, protected/invasive flags, and regional coverage.
4. Add consent and image-retention controls before storing user photos.
5. Build an admin review queue for uncertain IDs, corrections, rare species, and lookalike disagreements.
