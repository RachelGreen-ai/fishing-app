# ML Evaluation

This folder defines benchmark manifests, model prediction outputs, and metric scripts.

Large benchmark images should live outside git under:

```text
ml/data/benchmarks/fish_id_gold_v1/
```

Prediction files use JSONL:

```json
{"image_id":"gold_000001","predictions":[{"label":"largemouth-bass","score":0.93},{"label":"smallmouth-bass","score":0.04}],"latency_ms":142}
```

Evaluate classification predictions:

```bash
python3 ml/scripts/evaluate_predictions.py \
  ml/evaluation/examples/gold_manifest.example.jsonl \
  ml/evaluation/examples/predictions.example.jsonl
```

Evaluate size estimates:

```bash
python3 ml/scripts/evaluate_size_estimates.py \
  ml/evaluation/examples/size_manifest.example.jsonl \
  ml/evaluation/examples/size_predictions.example.jsonl
```

