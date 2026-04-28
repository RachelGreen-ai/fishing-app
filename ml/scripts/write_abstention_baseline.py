#!/usr/bin/env python3
"""Write the current image-only abstention baseline for a benchmark manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_jsonl", type=Path)
    parser.add_argument("output_jsonl", type=Path)
    return parser.parse_args()


def load_image_ids(path: Path) -> list[str]:
    image_ids = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_number}: invalid JSON: {exc}") from exc

            image_id = row.get("image_id")
            if not image_id:
                raise SystemExit(f"{path}:{line_number}: missing image_id")
            image_ids.append(str(image_id))
    return image_ids


def main() -> int:
    args = parse_args()
    image_ids = load_image_ids(args.manifest_jsonl)
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    with args.output_jsonl.open("w", encoding="utf-8") as handle:
        for image_id in image_ids:
            handle.write(
                json.dumps(
                    {
                        "image_id": image_id,
                        "predictions": [],
                        "abstained": True,
                        "latency_ms": 0,
                    },
                    sort_keys=True,
                )
            )
            handle.write("\n")

    print(f"Wrote {len(image_ids)} abstention predictions to {args.output_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
