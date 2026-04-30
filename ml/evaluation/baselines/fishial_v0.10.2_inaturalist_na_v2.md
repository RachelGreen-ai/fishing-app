# Fishial v0.10.2 Teacher Baseline On `inaturalist_na_v2`

Date: 2026-04-30

Teacher artifact:

- `classification_model_v0.10.2.zip`
- Source: `https://storage.googleapis.com/fishial-ml-resources/classification_model_v0.10.2.zip`
- Model metadata: DinoV2-224 + ViT Pooling 3 head + ArcFace + KNN
- Embedded teacher labels: 866

Evaluation setup:

- Manifest: `ml/data/classification/inaturalist_na_v2/test.manifest.jsonl`
- Images: 480
- Teacher top-k: 50
- Collapsed through: `ml/teacher_maps/fishial_v0.10.2_to_angler_v1.json`
- App taxonomy: `ml/fish_species_angler_v1.taxonomy.json`

## Metrics

Collapsed Fishial teacher:

- top-1 accuracy: `0.4833`
- top-3 accuracy: `0.6521`
- macro recall: `0.4833`
- angler-priority weighted top-1: `0.4013`
- angler-priority weighted top-3: `0.5870`
- mean latency: `70.16 ms/image` on local CPU

Current MobileNetV3Large student on the same split:

- top-1 accuracy: `0.7375`
- top-3 accuracy: `0.9375`
- macro recall: `0.7375`
- angler-priority weighted top-1: `0.7195`
- angler-priority weighted top-3: `0.9382`
- mean latency: `45.36 ms/image` on local CPU prediction script

## Interpretation

Fishial is not a drop-in replacement for our current 8 supported species. Its broader 866-class vocabulary often ranks species outside our app taxonomy above the supported app label, so collapsed top-1 is lower than our MobileNet student.

Fishial is still useful as a teacher for:

- unknown/out-of-taxonomy detection;
- pseudo-labeling broader angler species;
- finding hard negatives where the teacher strongly prefers a nearby unsupported species;
- distillation once our app taxonomy expands beyond 8 species.

The next teacher-student step should use Fishial top-k probabilities as soft labels and hard-negative signals, not replace the current bundled Core ML classifier directly.
