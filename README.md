# Catch ID

Phase 1 prototype for the fish identification plan in `fishing-app-plan.md`.

## Run

```bash
npm run dev
```

Open `http://127.0.0.1:4173`.

## iOS / Xcode

The native iOS project lives in `FishingApp.xcodeproj` and is generated from `project.yml` with XcodeGen.

Regenerate the project after changing `project.yml`:

```bash
xcodegen generate
```

Build from the command line:

```bash
xcodebuild -project FishingApp.xcodeproj -scheme FishingApp -destination 'generic/platform=iOS Simulator' -derivedDataPath /tmp/fishing-app-derived-data build
```

Open `FishingApp.xcodeproj` in Xcode to run the `FishingApp` scheme. The native target is a SwiftUI version of the identification MVP with photo selection, opt-in GPS range context, device date/time capture, privacy controls, evidence fields, confidence tiers, alternatives, and an on-device catch log.

## What Is Built

- Capture-first identification flow: take/select a photo first, then improve only if needed.
- Automatic context chips for date, time, season, saved/GPS-assisted range, and water type.
- Guided photo intake with client-side quality checks for resolution, lighting, contrast, and sharpness.
- Photo privacy controls for identification consent, optional de-identified training review, and retention policy.
- Collapsed improvement fields for region, water type, habitat, and visual traits.
- Native model transparency card showing the current Local Evidence Scorer and its limitations.
- Core ML/Vision classifier boundary ready for a bundled `FishSpeciesClassifier.mlmodel`.
- Local inference orchestrator with species scoring, location/date/habitat priors, top alternatives, confidence tiers, and cautious harvest language.
- Mock upload and scan-session APIs for upload metadata, scan creation, result retrieval, and feedback.
- Correction flow and local review queue for active-learning style feedback.
- Local catch log for confirmed or corrected IDs.

## Native ML Track

The iOS training and integration plan lives in [`docs/ios-ml-training-plan.md`](docs/ios-ml-training-plan.md). The first model artifact should be exported as `FishSpeciesClassifier.mlmodel` and added to the native app target.

## API Contract

The prototype exposes the first backend boundary:

- `POST /api/uploads` creates a mock signed-upload session from image metadata and consent.
- `POST /api/uploads/:id/complete` marks the mock upload metadata as captured.
- `POST /api/scans` creates a scan session from photo quality, context, and visual trait evidence.
- `GET /api/scans/:id` retrieves a scan result.
- `POST /api/scans/:id/feedback` records confirmations, alternatives, and manual corrections.

The current API stores upload metadata, scans, and feedback in server memory. It is meant to define the shape of the product workflow before adding object storage, persistent database tables, and a vendor model.

## Identification Model Boundary

The current classifier is a deterministic prototype in `src/inference.js`, called through the scan-session API in `server.js`. It is intentionally honest about uncertainty and should not be treated as a real computer-vision model.

The native production path should replace or augment this boundary:

1. Keep the `/api/scans` workflow as the UI contract.
2. Replace mock upload URLs with real signed upload URLs and object storage.
3. Route primary inference to the trained `FishSpeciesClassifier.mlmodel` on iOS, or to a server model with the same label IDs.
4. Preserve the local scoring concepts as calibration inputs: photo quality, location/date/habitat priors, lookalike groups, and abstention.
5. Store corrections and uncertain scans for review and future proprietary training data.

## Next Steps

1. Add persistent storage for uploads, scans, consent, feedback, and catch logs.
2. Integrate a fish-ID vendor behind an environment-configured service.
3. Expand the species catalog with canonical taxonomy, synonyms, protected/invasive flags, and regional coverage.
4. Add review queues for uncertain IDs, corrections, rare species, and lookalike disagreements.
5. Add location privacy controls before using GPS-level signals.
