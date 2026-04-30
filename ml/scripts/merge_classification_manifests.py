#!/usr/bin/env python3
"""Merge classification manifests with stable de-duplication."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_manifest_jsonl", type=Path)
    parser.add_argument("input_manifest_jsonl", type=Path, nargs="+")
    parser.add_argument("--labels-json", type=Path)
    parser.add_argument("--report-json", type=Path)
    return parser.parse_args()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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


def dedupe_key(row: dict) -> tuple[str, str]:
    source = str(row.get("source") or "")
    observation_id = row.get("source_observation_id")
    photo_id = row.get("source_photo_id")
    if source and observation_id and photo_id:
        return ("source-photo", f"{source}:{observation_id}:{photo_id}")
    if source and observation_id:
        return ("source-observation", f"{source}:{observation_id}")
    if row.get("source_path"):
        return ("source-path", str(row["source_path"]))
    return ("image-id", str(row.get("image_id") or row.get("image")))


def main() -> int:
    args = parse_args()
    allowed_species = None
    if args.labels_json:
        allowed_species = {row["id"] for row in load_json(args.labels_json)}

    seen = set()
    merged = []
    counters = Counter()
    counts_by_input = {}

    for manifest_path in args.input_manifest_jsonl:
        input_rows = load_jsonl(manifest_path)
        kept_for_input = 0
        for row in input_rows:
            species_id = row.get("species_id")
            if allowed_species is not None and species_id not in allowed_species:
                counters["skipped_label_not_allowed"] += 1
                continue

            key = dedupe_key(row)
            if key in seen:
                counters["skipped_duplicate"] += 1
                continue

            seen.add(key)
            merged.append(row)
            kept_for_input += 1
        counts_by_input[str(manifest_path)] = {
            "input_rows": len(input_rows),
            "kept_rows": kept_for_input,
        }

    args.output_manifest_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_manifest_jsonl.open("w", encoding="utf-8") as handle:
        for row in merged:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")

    report = {
        "output_manifest_jsonl": str(args.output_manifest_jsonl),
        "input_manifests": counts_by_input,
        "merged_rows": len(merged),
        "species_counts": dict(sorted(Counter(row["species_id"] for row in merged).items())),
        "counters": dict(counters),
    }
    report_path = args.report_json or args.output_manifest_jsonl.with_suffix(".report.json")
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
