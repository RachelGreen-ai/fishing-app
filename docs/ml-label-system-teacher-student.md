# Label System And Teacher-Student Plan

## Goal

The original 8-species classifier is fast on iPhone, but too narrow for a fishing app. The next label system should support:

- common angling species in North America and Europe;
- local range/date reranking;
- lookalike-group evaluation;
- graceful unsupported-species behavior;
- teacher-student distillation from broader external models.

## App Label Hierarchy

The app-owned taxonomy is `ml/fish_species_angler_v1.taxonomy.json`.

Each label has:

- `id`: stable app label id used by predictions and evaluation;
- `common_name` and `scientific_name`: user display plus teacher/dataset joins;
- `label_group`: broad family or routing group, such as `black-bass`, `salmonid`, `catfish`;
- `lookalike_group`: high-risk confusion group, such as `black-bass`, `trout-salmonid`, `red-coastal`;
- `app_regions`: `north-america`, `europe`, or both;
- `water_types` and `habitats`: local priors and filtering;
- `status`: `active`, `candidate`, `aggregate`, or `deprecated`.

Current `angler_v1` scope: 55 active species-level labels. This is intentionally smaller than Fishial's full vocabulary, but much broader than the 8-class MVP and friendlier for mobile UX.

## Fishial Teacher Mapping

Fishial's public `labels.json` is stored at `ml/external/fishial_labels.json`. The snapshot currently maps 775 numeric class ids to scientific names.

The generated map is `ml/teacher_maps/fishial_to_angler_v1.json`:

- teacher labels: 775
- app labels: 55
- mapped app labels: 54
- missing app labels: `chub`

Manual synonym overrides live in `ml/teacher_maps/fishial_manual_map_v1.json`.

## Evaluation Flow

1. Run Fishial teacher predictions on the same benchmark photos we use for MobileNet.
2. Collapse teacher predictions into app labels:

   ```bash
   python3 ml/scripts/collapse_teacher_predictions.py \
     ml/runs/fishial/angler_v1/test_teacher_predictions.jsonl \
     ml/teacher_maps/fishial_to_angler_v1.json \
     ml/runs/fishial/angler_v1/test_predictions_collapsed.jsonl
   ```

3. Evaluate the collapsed predictions:

   ```bash
   python3 ml/scripts/evaluate_predictions.py \
     ml/data/classification/inaturalist_angler_v1/test.manifest.jsonl \
     ml/runs/fishial/angler_v1/test_predictions_collapsed.jsonl
   ```

## Distillation Strategy

Use Fishial as a teacher, not the first mobile target:

- keep MobileNetV3Large or another small mobile model as the deployable student;
- use teacher top-k predictions to identify unsupported species and hard negatives;
- create soft-label training data from teacher probabilities;
- oversample field failures and lookalike groups;
- compare student against both ground truth and collapsed teacher predictions.

Promotion rule: the student model must improve app-label top-1, top-3, macro recall, lookalike-group recall, and unsupported-species abstention before replacing the bundled Core ML model.
