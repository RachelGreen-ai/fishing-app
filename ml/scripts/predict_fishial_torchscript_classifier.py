#!/usr/bin/env python3
"""Run a Fishial TorchScript classifier on a manifest and write prediction JSONL."""

from __future__ import annotations

import argparse
import json
import time
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageOps


IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_path", type=Path, help="TorchScript model, or a zip containing one.")
    parser.add_argument("labels_json", type=Path, help="Fallback Fishial labels JSON mapping class id to label.")
    parser.add_argument("manifest_jsonl", type=Path)
    parser.add_argument("image_root", type=Path)
    parser.add_argument("output_predictions_jsonl", type=Path)
    parser.add_argument("--image-height", type=int, default=154)
    parser.add_argument("--image-width", type=int, default=434)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--preprocess", choices=["square-pad", "center-crop", "stretch"], default="stretch")
    parser.add_argument(
        "--output-index",
        type=int,
        help="Optional output index for tuple/list TorchScript outputs. If omitted, the tensor matching label count is used.",
    )
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


def labels_from_json(path: Path) -> dict[int, str]:
    payload = load_json(path)
    if isinstance(payload, dict):
        return {int(key): str(value) for key, value in payload.items() if str(key).isdigit()}
    if isinstance(payload, list):
        labels = {}
        for index, item in enumerate(payload):
            if isinstance(item, str):
                labels[index] = item
            elif isinstance(item, dict):
                label = item.get("label") or item.get("scientific_name") or item.get("name")
                if label:
                    labels[int(item.get("id", index))] = str(label)
        return labels
    raise SystemExit("labels_json must be a dict or list")


def torchscript_path(path: Path) -> Path:
    if path.is_file() and path.suffix.lower() != ".zip":
        return path
    if path.is_dir():
        candidates = sorted(
            item
            for item in path.rglob("*")
            if item.is_file() and item.suffix.lower() in {".pt", ".pth", ".torchscript", ".ts"}
        )
        if not candidates:
            raise SystemExit(f"No TorchScript-like file found in {path}")
        return candidates[0]
    if path.suffix.lower() == ".zip":
        extract_root = path.with_suffix("")
        marker = extract_root / ".extracted"
        if not marker.exists():
            extract_root.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(path) as archive:
                archive.extractall(extract_root)
            marker.write_text("ok\n", encoding="utf-8")
        return torchscript_path(extract_root)
    raise SystemExit(f"Unsupported model path: {path}")


def labels_from_model(model, fallback_labels: dict[int, str]) -> dict[int, str]:
    try:
        if hasattr(model, "class_mapping_json_bytes"):
            json_bytes = bytes(model.class_mapping_json_bytes.cpu().tolist())
            class_mapping = json.loads(json_bytes.decode("utf-8"))
            labels = {}
            for key, value in class_mapping.items():
                label = value.get("label") if isinstance(value, dict) else value
                if label:
                    labels[int(key)] = str(label)
            if labels:
                return labels
    except Exception:
        pass
    return fallback_labels


def preprocess_image(path: Path, image_height: int, image_width: int, mode: str) -> torch.Tensor:
    image = Image.open(path).convert("RGB")
    if mode == "square-pad":
        width, height = image.size
        size = max(width, height)
        canvas = Image.new("RGB", (size, size), color=(0, 0, 0))
        canvas.paste(image, ((size - width) // 2, (size - height) // 2))
        image = canvas.resize((image_width, image_height), Image.Resampling.BILINEAR)
    elif mode == "center-crop":
        image = ImageOps.fit(image, (image_width, image_height), method=Image.Resampling.BILINEAR, centering=(0.5, 0.5))
    else:
        image = image.resize((image_width, image_height), Image.Resampling.BILINEAR)

    array = np.asarray(image, dtype=np.uint8).copy()
    tensor = torch.from_numpy(array).permute(2, 0, 1).float() / 255.0
    return (tensor - IMAGENET_MEAN) / IMAGENET_STD


def flatten_outputs(output: Any) -> list[torch.Tensor]:
    if isinstance(output, torch.Tensor):
        return [output]
    if isinstance(output, (tuple, list)):
        tensors = []
        for item in output:
            tensors.extend(flatten_outputs(item))
        return tensors
    if isinstance(output, dict):
        tensors = []
        for item in output.values():
            tensors.extend(flatten_outputs(item))
        return tensors
    return []


def select_logits(output: Any, label_ids: set[int], output_index: int | None) -> torch.Tensor:
    tensors = flatten_outputs(output)
    if not tensors:
        raise RuntimeError("TorchScript model did not return tensors")

    if output_index is not None:
        try:
            return tensors[output_index]
        except IndexError as exc:
            raise RuntimeError(f"Output index {output_index} not available; model returned {len(tensors)} tensors") from exc

    matching = [tensor for tensor in tensors if tensor.ndim >= 2 and set(range(int(tensor.shape[-1]))).issubset(label_ids)]
    if matching:
        return matching[-1]

    batched = [tensor for tensor in tensors if tensor.ndim >= 2]
    if batched:
        return max(batched, key=lambda tensor: int(tensor.shape[-1]))
    return tensors[-1]


def chunks(rows: list[dict], size: int):
    for index in range(0, len(rows), size):
        yield rows[index : index + size]


def main() -> int:
    args = parse_args()
    fallback_labels = labels_from_json(args.labels_json)
    rows = load_jsonl(args.manifest_jsonl)
    device = torch.device(args.device)
    model_file = torchscript_path(args.model_path)
    model = torch.jit.load(str(model_file), map_location=device)
    model.eval()
    labels = labels_from_model(model, fallback_labels)
    label_ids = set(labels)

    args.output_predictions_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_predictions_jsonl.open("w", encoding="utf-8") as handle, torch.inference_mode():
        for batch_rows in chunks(rows, args.batch_size):
            images = []
            kept_rows = []
            for row in batch_rows:
                image_path = args.image_root / row["image"]
                try:
                    images.append(preprocess_image(image_path, args.image_height, args.image_width, args.preprocess))
                    kept_rows.append(row)
                except Exception as exc:
                    raise RuntimeError(f"Could not load {image_path}: {exc}") from exc

            batch = torch.stack(images).to(device)
            start = time.perf_counter()
            output = model(batch)
            logits = select_logits(output, label_ids, args.output_index)
            probabilities = torch.softmax(logits, dim=-1).detach().cpu()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latency_ms = elapsed_ms / max(1, len(kept_rows))

            top_scores, top_indices = torch.topk(probabilities, k=min(args.top_k, len(labels)), dim=-1)
            for row, scores, indices in zip(kept_rows, top_scores, top_indices):
                predictions = [
                    {
                        "label": labels.get(int(index), f"Class {int(index)}"),
                        "teacher_id": str(int(index)),
                        "score": float(score),
                    }
                    for score, index in zip(scores, indices)
                ]
                handle.write(
                    json.dumps(
                        {
                            "image_id": row["image_id"],
                            "predictions": predictions,
                            "latency_ms": latency_ms,
                        },
                        sort_keys=True,
                    )
                )
                handle.write("\n")

    print(f"model_file={model_file}")
    print(f"labels={len(labels)}")
    print(f"wrote_predictions={args.output_predictions_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
