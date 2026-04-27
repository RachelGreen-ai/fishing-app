Fish Identification Capability Plan
Strategic Recommendation
Use a hybrid strategy:
Launch quickly with a fish-specific external API/model as a benchmark and fallback.
Build proprietary taxonomy, labeled data, inference orchestration, confidence calibration, and human review from day one.
Promote the proprietary model to primary only after it beats the external baseline on a blind production-like benchmark.
This is the best path because high accuracy depends less on a generic image model and more on angler-photo data, lookalike handling, location/date priors, calibrated uncertainty, and continuous correction loops.
Useful public references:
Catchr public positioning: https://getcatchr.com
Fishial.ai fish-recognition ecosystem and species coverage: https://fishial.ai/, https://docs.fishial.ai/api/specieslist
iNaturalist licensed images for public biodiversity photos: https://registry.opendata.aws/inaturalist-open-data/
FishNet fisheries image dataset initiative: https://www.fishnet.ai/
Fish-Vista trait and morphology dataset: https://github.com/Imageomics/Fish-Vista
Target Product Behavior
Build the identification flow as an evidence workflow, not a single photo guess.
Core user flow:
User opens Identify Fish.
App requests a clear side-profile photo.
Client checks blur, lighting, fish visibility, crop, and obstruction.
App asks for optional context: GPS, waterbody, freshwater/saltwater, date, habitat, and catch method.
Backend returns a confidence tier, top alternatives, distinguishing traits, and optional next-photo guidance.
User confirms, corrects, or saves to catch log.
Confidence UX:
Use tiers like Likely, Possible, Uncertain, and Not Enough Evidence instead of relying only on exact percentages.
Always show top alternatives for lookalike species.
Explain why the model thinks this species is likely: visual match, location support, season support, missing evidence, and lookalikes not ruled out.
For regulated or protected species, prefer caution over false certainty.
High-stakes flows:
Casual catch logging can accept one photo and low-friction confirmation.
Harvest/regulation guidance should require stronger confidence and location/date.
Leaderboards, tournaments, and records should require in-app capture, measuring-board evidence, metadata, duplicate detection, and human review for top submissions.
System Architecture
flowchart TD
    mobileApp[Mobile App] --> captureChecks[Capture Quality Checks]
    captureChecks --> uploadApi[Identification API]
    uploadApi --> objectStorage[Image Storage]
    uploadApi --> inferenceOrchestrator[Inference Orchestrator]
    inferenceOrchestrator --> detector[Fish Detector And Segmenter]
    detector --> classifier[Species Classifier]
    classifier --> priors[Location Date Habitat Priors]
    priors --> calibration[Confidence Calibration]
    calibration --> resultApi[Result And Alternatives]
    resultApi --> mobileApp
    mobileApp --> feedbackApi[Confirm Correct Feedback]
    feedbackApi --> reviewQueue[Human Review Queue]
    reviewQueue --> trainingData[Curated Training Data]
    trainingData --> trainingPipeline[Training Pipeline]
    trainingPipeline --> modelRegistry[Model Registry]
    modelRegistry --> inferenceOrchestrator
    inferenceOrchestrator --> externalApi[External Fish ID API Fallback]
Main components:
Mobile app: guided camera, upload queue, offline catch drafts, result UI, correction flow, privacy controls.
Identification API: scan sessions, signed upload URLs, analysis trigger, result retrieval, feedback capture.
Species catalog: canonical taxonomy, common names, scientific names, synonyms, regions, water type, lookalike groups, protected/invasive flags.
Inference orchestrator: quality scoring, detection/segmentation, classification, priors, calibration, fallback routing.
Data platform: raw images, processed crops, metadata, consent flags, labels, license lineage, dataset versions.
Labeling and review: user confirmations, expert review, disagreement resolution, active-learning queues.
Training and MLOps: model registry, benchmark sets, training jobs, shadow inference, canary deployment, drift monitoring.
Accuracy Strategy
Start with the top North American angling species, then expand by region.
Model stack:
Detector/segmenter to isolate fish from hands, boats, grass, decks, and measuring boards.
Fine-grained classifier for species, with top-k alternatives.
Embedding model for similarity search and active learning.
Hierarchical labels at family, genus, and species level to reduce lookalike mistakes.
Location/date/waterbody priors to re-rank plausible species.
Calibrated abstention so the system can say “not enough evidence.”
Training data sources:
Licensed public data: iNaturalist, FishNet, Fish-Vista, NOAA/USGS where licensing permits commercial ML use.
Vendor/API outputs for benchmark comparison, not as unquestioned labels.
Consented in-app angler photos, which become the strongest proprietary asset.
Expert-reviewed gold sets for lookalikes, protected species, rare species, and leaderboard submissions.
Evaluation gates:
Do not use only random train/test splits; split by user, source, geography, and waterbody to avoid leakage.
Track top-1 accuracy, top-3 accuracy, calibrated confidence, abstention rate, correction rate, protected-species false positives, and lookalike confusion clusters.
Maintain separate benchmarks for North American freshwater, North American saltwater, low-quality photos, juveniles, rare/protected species, and out-of-region cases.
Development Roadmap
Phase 0: Discovery and benchmark, 2-4 weeks
Define initial species catalog for North American freshwater and saltwater angling species.
Group species by region, water type, and lookalike risk.
Benchmark Fishial.ai or comparable vendors against a blind image set.
Define consent, image retention, location privacy, and commercial training rights.
Create success thresholds for MVP, private beta, public launch, and proprietary-model promotion.
Phase 1: MVP identification flow, 6-10 weeks
Build mobile capture flow with quality checks and guided retakes.
Implement backend scan sessions, signed uploads, result retrieval, and feedback endpoints.
Integrate external fish ID API as primary inference path.
Build species catalog and result UI with confidence tiers and alternatives.
Add analytics for latency, failure rate, confidence distribution, correction rate, and vendor cost per scan.
Phase 2: Data and labeling foundation, 4-8 weeks in parallel
Build data lake for raw photos, crops, metadata, consent, labels, and model outputs.
Add deduplication, EXIF handling, license tracking, and privacy controls.
Create review queues for uncertain IDs, vendor/model disagreements, rare species, and leaderboard candidates.
Recruit expert labelers or advisors for taxonomy and gold-label validation.
Start collecting consented app photos as training candidates.
Phase 3: Proprietary baseline model, 8-12 weeks
Train first fish detector/segmenter and species classifier from licensed public data plus curated app data.
Run proprietary model in shadow mode beside the external API.
Compare per-species accuracy, top-3 accuracy, latency, and calibration.
Add location/date/waterbody priors and confidence calibration.
Identify top confusion clusters and prioritize data collection for those species.
Phase 4: Hybrid production inference, 6-10 weeks
Deploy inference orchestrator with routing rules.
Use proprietary model when confidence is high and species is supported.
Use external API fallback when unsupported, low-confidence, or model disagreement is high.
Add human-review escalation for high-impact cases.
Roll out canary traffic by region and species group.
Start reducing vendor dependency when proprietary performance clears release gates.
Phase 5: Measurement, logging, and leaderboards, 8-12 weeks
Add catch log with species, photos, location privacy, weight, length, bait, notes, and weather/water metadata.
Implement measurement flow using measuring board/reference object requirements.
Separate estimated measurement from verified leaderboard measurement.
Add anti-cheat: in-app camera preference, timestamp/GPS metadata, duplicate photo detection, manipulation checks, and manual review.
Build leaderboard moderation states: Auto-verified, Pending Review, Needs More Evidence, and Rejected.
Phase 6: Offline and global expansion, ongoing
Add downloadable regional species packs for common species and offline catch logging.
Cache regulations or conservation info only with source and last-updated date.
Expand globally region by region with local taxonomy, common names, range priors, local experts, and separate benchmarks.
Add regional model heads or routing where global classification degrades local accuracy.
Team And Workstreams
Recommended core team:
1 product manager for identification, logging, and verification workflows.
1 designer for capture UX, uncertainty UX, and correction flows.
2 mobile engineers for iOS/Android or cross-platform app.
2 backend engineers for APIs, storage, auth, species catalog, and admin tools.
2 ML engineers for detection, classification, calibration, and inference serving.
1 data engineer for datasets, lineage, labeling exports, and analytics.
1 MLOps/platform engineer for model registry, deployment, observability, and cost control.
Part-time privacy/security counsel and ichthyology experts.
Workstreams:
Product UX: capture, result explanation, correction, logging, verification.
Backend platform: scan lifecycle, species catalog, storage, feedback, admin review.
ML platform: inference, benchmark, training, calibration, model registry.
Data quality: taxonomy, labels, licenses, dedupe, expert review.
Trust and safety: regulations, conservation, leaderboards, anti-cheat, privacy.
Key Risks And Mitigations
Domain shift: public datasets differ from angler photos. Mitigate by prioritizing consented in-app data and expert-reviewed production examples.
Lookalike species: bass, sunfish, trout, rockfish, snapper, grouper, tuna, and juveniles can be subtle. Mitigate with top-k alternatives, adaptive extra-photo prompts, and lookalike-specific review.
Overconfidence: wrong IDs can affect harvest decisions. Mitigate with calibrated confidence, abstention, and cautious regulated-species language.
Location prior errors: stocked, invasive, transported, or aquarium fish can appear outside normal range. Mitigate by re-ranking rather than hard-filtering.
Measurement fraud: image-only weight is unreliable. Mitigate by using length/girth/reference workflows and human review for competition.
Dataset licensing: public images may not allow commercial model training. Mitigate with strict license lineage and consent controls.
Global expansion: taxonomy, names, regulations, and appearance vary regionally. Mitigate with regional releases and benchmarks.
Definition Of Success
MVP success:
Users can identify, correct, and log common North American catches with clear uncertainty handling.
Median scan latency is acceptable for mobile use.
Feedback and consented training data collection are working.
Vendor cost per scan and failure rates are measurable.
Accuracy success:
Top-3 accuracy is high enough that the correct fish usually appears among alternatives.
Top-1 accuracy is strong for high-volume target species.
Confidence is calibrated: high-confidence predictions are actually reliable.
Correction rate falls over time for target species and regions.
Business moat:
Proprietary angler-photo dataset grows continuously.
Expert-reviewed gold labels cover the hardest lookalike groups.
Proprietary model gradually replaces vendor dependency for priority species.
The product earns user trust by explaining uncertainty rather than hiding it.
