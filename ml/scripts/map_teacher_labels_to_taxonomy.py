#!/usr/bin/env python3
"""Map external teacher-model labels onto the app fish taxonomy."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("taxonomy_json", type=Path)
    parser.add_argument("teacher_labels_json", type=Path)
    parser.add_argument("output_map_json", type=Path)
    parser.add_argument(
        "--manual-map-json",
        type=Path,
        help="Optional overrides. Supports {'teacher_to_app': {'label-or-id': 'app-id'}}.",
    )
    return parser.parse_args()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def load_teacher_labels(payload: Any) -> list[dict]:
    if isinstance(payload, dict):
        return [
            {"teacher_id": str(key), "teacher_label": str(value)}
            for key, value in sorted(payload.items(), key=lambda item: int(item[0]) if str(item[0]).isdigit() else str(item[0]))
        ]

    if isinstance(payload, list):
        rows = []
        for index, item in enumerate(payload):
            if isinstance(item, str):
                rows.append({"teacher_id": str(index), "teacher_label": item})
            elif isinstance(item, dict):
                label = item.get("label") or item.get("name") or item.get("scientific_name") or item.get("common_name")
                if not label:
                    continue
                rows.append({"teacher_id": str(item.get("id", index)), "teacher_label": str(label)})
        return rows

    raise SystemExit("Teacher labels must be a dict or list")


def main() -> int:
    args = parse_args()
    taxonomy = load_json(args.taxonomy_json)
    teacher_rows = load_teacher_labels(load_json(args.teacher_labels_json))
    manual_map = load_json(args.manual_map_json) if args.manual_map_json else {}
    teacher_to_app_override = {
        normalize(str(key)): str(value)
        for key, value in (manual_map.get("teacher_to_app") or {}).items()
    }

    app_by_id = {row["id"]: row for row in taxonomy}
    scientific_to_app: dict[str, list[str]] = defaultdict(list)
    common_to_app: dict[str, list[str]] = defaultdict(list)
    id_to_app: dict[str, str] = {}
    for row in taxonomy:
        id_to_app[normalize(row["id"])] = row["id"]
        scientific_to_app[normalize(row["scientific_name"])].append(row["id"])
        common_to_app[normalize(row["common_name"])].append(row["id"])
        for alias in row.get("aliases", []):
            common_to_app[normalize(alias)].append(row["id"])

    mapped_teacher_labels = {}
    app_to_teacher: dict[str, list[dict]] = defaultdict(list)
    unmatched_teacher_labels = []

    for teacher in teacher_rows:
        teacher_id = teacher["teacher_id"]
        teacher_label = teacher["teacher_label"]
        normalized_label = normalize(teacher_label)
        normalized_id = normalize(teacher_id)
        app_id = None
        match_type = None

        if normalized_label in teacher_to_app_override:
            app_id = teacher_to_app_override[normalized_label]
            match_type = "manual_label"
        elif normalized_id in teacher_to_app_override:
            app_id = teacher_to_app_override[normalized_id]
            match_type = "manual_id"
        elif normalized_label in scientific_to_app and len(scientific_to_app[normalized_label]) == 1:
            app_id = scientific_to_app[normalized_label][0]
            match_type = "exact_scientific_name"
        elif normalized_label in common_to_app and len(common_to_app[normalized_label]) == 1:
            app_id = common_to_app[normalized_label][0]
            match_type = "exact_common_name"
        elif normalized_label in id_to_app:
            app_id = id_to_app[normalized_label]
            match_type = "exact_app_id"

        if app_id and app_id not in app_by_id:
            raise SystemExit(f"Manual map points to unknown app id: {app_id}")

        if app_id:
            row = {
                "teacher_id": teacher_id,
                "teacher_label": teacher_label,
                "app_id": app_id,
                "match_type": match_type,
            }
            mapped_teacher_labels[teacher_label] = row
            app_to_teacher[app_id].append(row)
        else:
            unmatched_teacher_labels.append(teacher)

    app_labels_missing_teacher = sorted(set(app_by_id) - set(app_to_teacher))
    output = {
        "app_taxonomy_json": str(args.taxonomy_json),
        "teacher_labels_json": str(args.teacher_labels_json),
        "summary": {
            "app_label_count": len(app_by_id),
            "teacher_label_count": len(teacher_rows),
            "mapped_teacher_label_count": len(mapped_teacher_labels),
            "mapped_app_label_count": len(app_to_teacher),
            "app_labels_missing_teacher_count": len(app_labels_missing_teacher),
        },
        "mapped_teacher_labels": mapped_teacher_labels,
        "app_to_teacher": dict(sorted(app_to_teacher.items())),
        "app_labels_missing_teacher": app_labels_missing_teacher,
        "unmatched_teacher_labels": unmatched_teacher_labels,
    }

    args.output_map_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_map_json.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(output["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
