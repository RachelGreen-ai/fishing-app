#!/usr/bin/env python3
"""Evaluate fish species prediction JSONL against a golden manifest."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


UNKNOWN_LABEL = "unknown"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_jsonl", type=Path)
    parser.add_argument("predictions_jsonl", type=Path)
    parser.add_argument("--threshold", type=float, default=0.0)
    parser.add_argument("--ece-bins", type=int, default=10)
    parser.add_argument("--prior-json", type=Path, help="Optional angler-priority prior JSON.")
    parser.add_argument("--prior-region", help="Region key inside --prior-json, such as europe.")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_number}: invalid JSON: {exc}") from exc
    return rows


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_priority_weights(path: Path | None, region: str | None) -> dict[str, float]:
    if not path:
        return {}
    if not region:
        raise SystemExit("--prior-region is required when --prior-json is provided")

    prior = load_json(path)
    regions = prior.get("regions") or {}
    if region not in regions:
        available = ", ".join(sorted(regions)) or "<none>"
        raise SystemExit(f"Region {region!r} not found in {path}. Available regions: {available}")

    raw_weights = regions[region].get("species_weights") or {}
    weights = {str(species_id): float(weight) for species_id, weight in raw_weights.items()}
    if any(weight <= 0 for weight in weights.values()):
        raise SystemExit("Priority weights must be positive numbers")
    if not weights:
        raise SystemExit(f"No species_weights found for region {region!r} in {path}")
    return weights


def top_labels(row: dict) -> list[str]:
    predictions = row.get("predictions") or []
    return [str(item.get("label", "")) for item in predictions if item.get("label")]


def top_score(row: dict) -> float:
    predictions = row.get("predictions") or []
    if not predictions:
        return 0.0
    return float(predictions[0].get("score", 0.0))


def expected_calibration_error(confidences: list[float], correct: list[bool], bins: int) -> float:
    if not confidences:
        return 0.0

    total = len(confidences)
    ece = 0.0
    for index in range(bins):
        low = index / bins
        high = (index + 1) / bins
        in_bin = [
            item_index
            for item_index, confidence in enumerate(confidences)
            if low <= confidence < high or (index == bins - 1 and confidence == 1.0)
        ]
        if not in_bin:
            continue
        bin_confidence = mean(confidences[item_index] for item_index in in_bin)
        bin_accuracy = mean(1.0 if correct[item_index] else 0.0 for item_index in in_bin)
        ece += (len(in_bin) / total) * abs(bin_accuracy - bin_confidence)
    return ece


def weighted_sum(rows: list[dict], species_counts: Counter, weights: dict[str, float]) -> float:
    total = 0.0
    for row in rows:
        species_id = row["species_id"]
        species_count = species_counts.get(species_id, 0)
        if species_count and species_id in weights:
            total += weights[species_id] / species_count
    return total


def weighted_accuracy(
    rows: list[dict],
    species_counts: Counter,
    weights: dict[str, float],
    metric_key: str,
) -> float | None:
    denominator = weighted_sum(rows, species_counts, weights)
    if denominator == 0:
        return None
    numerator = 0.0
    for row in rows:
        species_id = row["species_id"]
        species_count = species_counts.get(species_id, 0)
        if species_count and species_id in weights and row[metric_key]:
            numerator += weights[species_id] / species_count
    return numerator / denominator


def main() -> int:
    args = parse_args()
    manifest_rows = load_jsonl(args.manifest_jsonl)
    prediction_rows = {row["image_id"]: row for row in load_jsonl(args.predictions_jsonl)}
    priority_weights = load_priority_weights(args.prior_json, args.prior_region)

    missing_predictions = []
    evaluated = []
    by_species: dict[str, Counter] = defaultdict(Counter)
    by_lookalike: dict[str, Counter] = defaultdict(Counter)
    predicted_by_species: Counter = Counter()
    confidences = []
    confidence_correct = []
    latencies = []
    unknown_total = 0
    unknown_abstained = 0

    for truth in manifest_rows:
        image_id = truth["image_id"]
        species_id = truth["species_id"]
        prediction = prediction_rows.get(image_id)
        if prediction is None:
            missing_predictions.append(image_id)
            continue

        labels = top_labels(prediction)
        score = top_score(prediction)
        abstained = bool(prediction.get("abstained")) or score < args.threshold or not labels
        top1 = labels[0] if labels else UNKNOWN_LABEL

        is_unknown = species_id == UNKNOWN_LABEL
        if is_unknown:
            unknown_total += 1
            if abstained:
                unknown_abstained += 1

        top1_correct = not abstained and top1 == species_id
        top3_correct = not abstained and species_id in labels[:3]

        if not is_unknown:
            by_species[species_id]["total"] += 1
            by_species[species_id]["top1"] += int(top1_correct)
            by_species[species_id]["top3"] += int(top3_correct)
            if not abstained and top1 != UNKNOWN_LABEL:
                predicted_by_species[top1] += 1

        lookalike_group = truth.get("lookalike_group") or ""
        if lookalike_group and not is_unknown:
            by_lookalike[lookalike_group]["total"] += 1
            by_lookalike[lookalike_group]["top1"] += int(top1_correct)
            by_lookalike[lookalike_group]["top3"] += int(top3_correct)

        if not abstained:
            confidences.append(score)
            confidence_correct.append(top1_correct)

        if "latency_ms" in prediction:
            latencies.append(float(prediction["latency_ms"]))

        evaluated.append(
            {
                "image_id": image_id,
                "species_id": species_id,
                "abstained": abstained,
                "top1_correct": top1_correct,
                "top3_correct": top3_correct,
                "score": score,
            }
        )

    if missing_predictions:
        raise SystemExit(f"Missing predictions for {len(missing_predictions)} images: {missing_predictions[:5]}")

    known = [row for row in evaluated if row["species_id"] != UNKNOWN_LABEL]
    covered_known = [row for row in known if not row["abstained"]]
    known_species_counts = Counter(row["species_id"] for row in known)
    coverage = len(covered_known) / len(known) if known else 0.0
    top1 = mean(1.0 if row["top1_correct"] else 0.0 for row in known) if known else 0.0
    top3 = mean(1.0 if row["top3_correct"] else 0.0 for row in known) if known else 0.0
    selective_top1 = (
        mean(1.0 if row["top1_correct"] else 0.0 for row in covered_known)
        if covered_known
        else 0.0
    )
    macro_recall = (
        mean(counts["top1"] / counts["total"] for counts in by_species.values() if counts["total"])
        if by_species
        else 0.0
    )
    unknown_abstention_recall = unknown_abstained / unknown_total if unknown_total else None

    report = {
        "count": len(evaluated),
        "known_count": len(known),
        "coverage": round(coverage, 4),
        "top1_accuracy": round(top1, 4),
        "top3_accuracy": round(top3, 4),
        "selective_top1_accuracy": round(selective_top1, 4),
        "macro_recall": round(macro_recall, 4),
        "unknown_abstention_recall": (
            round(unknown_abstention_recall, 4) if unknown_abstention_recall is not None else None
        ),
        "expected_calibration_error": round(
            expected_calibration_error(confidences, confidence_correct, args.ece_bins),
            4,
        ),
        "mean_latency_ms": round(mean(latencies), 2) if latencies else None,
        "per_species": {
            species: {
                "count": counts["total"],
                "predicted_count": predicted_by_species[species],
                "precision": (
                    round(counts["top1"] / predicted_by_species[species], 4)
                    if predicted_by_species[species]
                    else None
                ),
                "top1_recall": round(counts["top1"] / counts["total"], 4),
                "top3_recall": round(counts["top3"] / counts["total"], 4),
                "f1": (
                    round(
                        2
                        * (counts["top1"] / predicted_by_species[species])
                        * (counts["top1"] / counts["total"])
                        / ((counts["top1"] / predicted_by_species[species]) + (counts["top1"] / counts["total"])),
                        4,
                    )
                    if predicted_by_species[species] and counts["top1"]
                    else 0.0
                ),
            }
            for species, counts in sorted(by_species.items())
            if counts["total"]
        },
        "lookalike_groups": {
            group: {
                "count": counts["total"],
                "top1": round(counts["top1"] / counts["total"], 4),
                "top3": round(counts["top3"] / counts["total"], 4),
            }
            for group, counts in sorted(by_lookalike.items())
            if counts["total"]
        },
    }

    if priority_weights:
        evaluated_species = set(known_species_counts)
        weighted_coverage_denominator = weighted_sum(known, known_species_counts, priority_weights)
        weighted_coverage = (
            weighted_sum(covered_known, known_species_counts, priority_weights) / weighted_coverage_denominator
            if weighted_coverage_denominator
            else 0.0
        )
        weighted_top1 = weighted_accuracy(known, known_species_counts, priority_weights, "top1_correct")
        weighted_top3 = weighted_accuracy(known, known_species_counts, priority_weights, "top3_correct")
        weighted_selective_top1 = weighted_accuracy(
            covered_known,
            known_species_counts,
            priority_weights,
            "top1_correct",
        )
        report["priority_weighted"] = {
            "region": args.prior_region,
            "coverage": round(weighted_coverage, 4),
            "top1_accuracy": round(weighted_top1, 4) if weighted_top1 is not None else None,
            "top3_accuracy": round(weighted_top3, 4) if weighted_top3 is not None else None,
            "selective_top1_accuracy": (
                round(weighted_selective_top1, 4) if weighted_selective_top1 is not None else None
            ),
            "prior_weight_evaluated": round(
                sum(priority_weights[species] for species in evaluated_species if species in priority_weights),
                4,
            ),
            "prior_weight_missing_from_eval": round(
                sum(weight for species, weight in priority_weights.items() if species not in evaluated_species),
                4,
            ),
            "species_missing_from_eval": sorted(set(priority_weights) - evaluated_species),
            "species_missing_from_prior": sorted(evaluated_species - set(priority_weights)),
        }

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
