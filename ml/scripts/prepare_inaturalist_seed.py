#!/usr/bin/env python3
"""Prepare a species classification seed manifest from public iNaturalist photos."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


API_ROOT = "https://api.inaturalist.org/v1"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
SOURCE_NAME = "inaturalist"
ALLOWED_LICENSES = {
    "cc0",
    "cc-by",
    "cc-by-nc",
    "cc-by-sa",
    "cc-by-nc-sa",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--labels", type=Path, default=Path("ml/fish_species_v1.labels.json"))
    parser.add_argument("--taxonomy-json", type=Path, default=Path("ml/fish_species_v1.taxonomy.json"))
    parser.add_argument("--max-per-species", type=int, default=250)
    parser.add_argument("--min-per-species", type=int, default=50)
    parser.add_argument("--per-page", type=int, default=200)
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--image-size", choices=["medium", "large", "original"], default="medium")
    parser.add_argument(
        "--species-ids",
        nargs="+",
        help="Optional subset of label ids to fetch, useful for targeted enrichment of weak classes.",
    )
    parser.add_argument(
        "--exclude-manifest-jsonl",
        type=Path,
        action="append",
        default=[],
        help="Existing manifest(s) whose source_observation_id values should not be downloaded again.",
    )
    parser.add_argument("--resume", action="store_true")
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


def excluded_observation_ids(paths: list[Path]) -> set[int]:
    excluded = set()
    for path in paths:
        for row in load_jsonl(path):
            observation_id = row.get("source_observation_id")
            if observation_id is not None:
                excluded.add(int(observation_id))
    return excluded


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def request_json(url: str, retries: int = 3) -> dict:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "fishing-app-ml/0.1"})
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(1 + attempt)
    raise SystemExit(f"Failed to fetch {url}: {last_error}")


def download_file(url: str, destination: Path, retries: int = 3) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "fishing-app-ml/0.1"})
            with urllib.request.urlopen(request, timeout=45) as response, temporary.open("wb") as handle:
                shutil.copyfileobj(response, handle)
            if temporary.stat().st_size == 0:
                raise OSError("downloaded empty file")
            temporary.replace(destination)
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if temporary.exists():
                temporary.unlink()
            time.sleep(1 + attempt)
    raise RuntimeError(f"Failed to download {url}: {last_error}")


def resolve_taxon_id(scientific_name: str) -> int:
    params = urllib.parse.urlencode({"q": scientific_name, "rank": "species", "per_page": 10})
    payload = request_json(f"{API_ROOT}/taxa?{params}")
    normalized = scientific_name.lower()
    for row in payload.get("results", []):
        if str(row.get("name", "")).lower() == normalized:
            return int(row["id"])
    if payload.get("results"):
        return int(payload["results"][0]["id"])
    raise SystemExit(f"No iNaturalist taxon found for {scientific_name}")


def image_url(photo: dict, size: str) -> str | None:
    url = photo.get("url")
    if not url:
        return None
    if size == "original":
        return photo.get("original_url") or url.replace("square.", "original.")
    return url.replace("square.", f"{size}.")


def extension_from_url(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    suffix = Path(path).suffix.lower()
    return suffix if suffix in IMAGE_EXTENSIONS else ".jpg"


def observation_rows(taxon_id: int, per_page: int, page: int) -> list[dict]:
    params = urllib.parse.urlencode(
        {
            "taxon_id": taxon_id,
            "quality_grade": "research",
            "photos": "true",
            "order_by": "created_at",
            "order": "desc",
            "per_page": per_page,
            "page": page,
        }
    )
    payload = request_json(f"{API_ROOT}/observations?{params}")
    return payload.get("results", [])


def first_allowed_photo(observation: dict, size: str) -> tuple[dict, str] | None:
    for photo in observation.get("photos") or []:
        license_code = str(photo.get("license_code") or "").lower()
        if license_code not in ALLOWED_LICENSES:
            continue
        url = image_url(photo, size)
        if url:
            return photo, url
    return None


def infer_quality(observation: dict) -> str:
    quality_grade = observation.get("quality_grade")
    if quality_grade == "research":
        return "medium"
    return "low"


def species_rows(
    args: argparse.Namespace,
    label: dict,
    taxon_id: int,
    excluded_observations: set[int],
) -> tuple[list[dict], Counter]:
    species_id = label["id"]
    species_root = args.output_root / "images" / species_id
    rows = []
    counters = Counter()
    seen_observations = set()
    page = 1

    while len(rows) < args.max_per_species:
        observations = observation_rows(taxon_id, args.per_page, page)
        if not observations:
            break

        for observation in observations:
            if len(rows) >= args.max_per_species:
                break
            observation_id = observation.get("id")
            if not observation_id or observation_id in seen_observations:
                continue
            seen_observations.add(observation_id)
            if int(observation_id) in excluded_observations:
                counters["skipped_excluded_observation"] += 1
                continue
            selected = first_allowed_photo(observation, args.image_size)
            if not selected:
                counters["skipped_no_allowed_photo_license"] += 1
                continue

            photo, url = selected
            image_index = len(rows) + 1
            image_id = f"inat_{species_id}_{image_index:05d}"
            destination = species_root / f"{image_id}{extension_from_url(url)}"
            if not destination.exists() or not args.resume:
                try:
                    download_file(url, destination)
                except RuntimeError:
                    counters["download_failed"] += 1
                    continue

            rows.append(
                {
                    "image_id": image_id,
                    "image": str(destination.relative_to(args.output_root)),
                    "species_id": species_id,
                    "scientific_name": label["scientific_name"],
                    "split": "seed",
                    "scenario_tags": ["public-seed", "field", "catch-or-wild"],
                    "lookalike_group": "",
                    "region": "north-america",
                    "water_type": "",
                    "quality": infer_quality(observation),
                    "source": SOURCE_NAME,
                    "license": str(photo.get("license_code") or ""),
                    "source_species_name": label["scientific_name"],
                    "source_observation_id": observation_id,
                    "source_photo_id": photo.get("id"),
                    "source_url": observation.get("uri"),
                    "source_path": str(destination),
                }
            )
            counters["downloaded"] += 1

        page += 1
        time.sleep(args.sleep)

    return rows, counters


def main() -> int:
    args = parse_args()
    labels = load_json(args.labels)
    if args.species_ids:
        requested = set(args.species_ids)
        labels = [label for label in labels if label["id"] in requested]
        missing = sorted(requested - {label["id"] for label in labels})
        if missing:
            raise SystemExit(f"Requested species ids were not found in labels: {missing}")

    taxonomy = load_json(args.taxonomy_json)
    taxonomy_by_id = {row["id"]: row for row in taxonomy}
    excluded_observations = excluded_observation_ids(args.exclude_manifest_jsonl)
    args.output_root.mkdir(parents=True, exist_ok=True)

    all_rows = []
    report = {
        "source": SOURCE_NAME,
        "output_root": str(args.output_root),
        "max_per_species": args.max_per_species,
        "min_per_species": args.min_per_species,
        "species": {},
    }

    for label in labels:
        species_id = label["id"]
        taxon_id = resolve_taxon_id(label["scientific_name"])
        rows, counters = species_rows(args, label, taxon_id, excluded_observations)
        if len(rows) < args.min_per_species:
            report["species"][species_id] = {
                "taxon_id": taxon_id,
                "status": "below_minimum",
                "matched_images": len(rows),
                "counters": dict(counters),
            }
            continue

        species_taxonomy = taxonomy_by_id.get(species_id, {})
        for row in rows:
            for field in ("family", "family_common", "label_group", "lookalike_group", "taxon_rank", "is_species_level"):
                row[field] = species_taxonomy.get(field, row.get(field, ""))

        all_rows.extend(rows)
        report["species"][species_id] = {
            "taxon_id": taxon_id,
            "status": "included",
            "matched_images": len(rows),
            "counters": dict(counters),
        }

    manifest_path = args.output_root / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as handle:
        for row in all_rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")

    report["matched_total"] = len(all_rows)
    report["included_species"] = sorted(
        species_id for species_id, row in report["species"].items() if row["status"] == "included"
    )
    (args.output_root / "source_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
