#!/usr/bin/env python3
"""Prepare a QUT FISH Kaggle seed benchmark manifest for the MVP fish labels."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
DEFAULT_LICENSE = "CC BY-SA 3.0"
DEFAULT_SOURCE = "qut-fish-kaggle"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("qut_root", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--labels", type=Path, default=Path("ml/fish_species_v1.labels.json"))
    parser.add_argument("--aliases", type=Path, default=Path("ml/fish_species_v1.aliases.json"))
    parser.add_argument("--mode", choices=["manifest-only", "symlink", "copy"], default="manifest-only")
    parser.add_argument("--prefer", choices=["cropped", "raw_images", "any"], default="cropped")
    parser.add_argument("--max-per-species", type=int, default=0)
    return parser.parse_args()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[-_\\/]+", " ", value)
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def load_alias_lookup(labels_path: Path, aliases_path: Path) -> dict[str, str]:
    labels = load_json(labels_path)
    aliases = load_json(aliases_path)
    lookup: dict[str, str] = {}

    for row in labels:
        label_id = row["id"]
        names = {label_id, row["common_name"], row["scientific_name"], *aliases.get(label_id, [])}
        for name in names:
            lookup[normalize(name)] = label_id

    return lookup


def candidate_images(qut_root: Path, prefer: str) -> list[Path]:
    images = [
        path
        for path in qut_root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]

    if prefer == "any":
        return sorted(images)

    preferred = [path for path in images if prefer in {normalize(part) for part in path.parts}]
    return sorted(preferred or images)


def infer_species_id(path: Path, qut_root: Path, alias_lookup: dict[str, str]) -> str | None:
    relative = path.relative_to(qut_root)
    parts = [normalize(part) for part in relative.parts[:-1]]
    filename = normalize(path.stem)

    for part in reversed(parts):
        if part in alias_lookup:
            return alias_lookup[part]

    for alias, label_id in alias_lookup.items():
        if alias and (alias in filename or alias in " ".join(parts)):
            return label_id

    return None


def infer_tags(path: Path) -> tuple[list[str], str]:
    text = normalize(" ".join(path.parts))
    tags = set()
    quality = "medium"

    if "cropped" in text:
        tags.update(["cropped", "side-profile"])
        quality = "high"
    if "raw images" in text or "raw image" in text:
        tags.add("raw")
    if "controlled" in text:
        tags.update(["controlled", "side-profile"])
        quality = "high"
    if "out of the water" in text or "out of water" in text or "out-of-the-water" in text:
        tags.update(["out-of-water", "field"])
    if "in situ" in text or "in-situ" in text:
        tags.update(["in-situ", "underwater"])

    if not tags:
        tags.update(["public-seed"])

    return sorted(tags), quality


def materialize_image(source: Path, destination: Path, mode: str) -> None:
    if mode == "manifest-only":
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return

    if mode == "copy":
        shutil.copy2(source, destination)
    else:
        os.symlink(source.resolve(), destination)


def main() -> int:
    args = parse_args()
    if not args.qut_root.exists():
        raise SystemExit(f"QUT root does not exist: {args.qut_root}")

    alias_lookup = load_alias_lookup(args.labels, args.aliases)
    args.output_root.mkdir(parents=True, exist_ok=True)
    images_root = args.output_root / "images"
    manifest_path = args.output_root / "manifest.jsonl"
    unmatched_path = args.output_root / "unmatched_species_report.json"

    matched_counts = Counter()
    unmatched_counts = Counter()
    rows = []

    for image_path in candidate_images(args.qut_root, args.prefer):
        species_id = infer_species_id(image_path, args.qut_root, alias_lookup)
        if not species_id:
            parent_hint = " / ".join(image_path.relative_to(args.qut_root).parts[:-1])
            unmatched_counts[parent_hint or "<root>"] += 1
            continue

        if args.max_per_species and matched_counts[species_id] >= args.max_per_species:
            continue

        matched_counts[species_id] += 1
        image_id = f"qut_{species_id}_{matched_counts[species_id]:05d}"
        destination = images_root / species_id / f"{image_id}{image_path.suffix.lower()}"
        materialize_image(image_path, destination, args.mode)
        tags, quality = infer_tags(image_path)

        rows.append(
            {
                "image_id": image_id,
                "image": str(destination.relative_to(args.output_root)),
                "species_id": species_id,
                "scientific_name": "",
                "split": "gold",
                "scenario_tags": tags,
                "lookalike_group": "",
                "region": "",
                "water_type": "",
                "quality": quality,
                "source": DEFAULT_SOURCE,
                "license": DEFAULT_LICENSE,
                "source_path": str(image_path),
            }
        )

    with manifest_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")

    report = {
        "qut_root": str(args.qut_root),
        "output_root": str(args.output_root),
        "mode": args.mode,
        "matched_total": len(rows),
        "matched_per_species": dict(sorted(matched_counts.items())),
        "unmatched_directory_count": len(unmatched_counts),
        "top_unmatched_directories": unmatched_counts.most_common(50),
    }
    unmatched_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
