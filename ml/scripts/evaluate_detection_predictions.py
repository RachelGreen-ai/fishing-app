#!/usr/bin/env python3
"""Evaluate fish detector JSONL predictions against a detection manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_jsonl", type=Path)
    parser.add_argument("predictions_jsonl", type=Path)
    parser.add_argument("--score-threshold", type=float, default=0.25)
    parser.add_argument("--iou-threshold", type=float, default=0.5)
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


def annotation_xyxy(annotation: dict) -> list[float]:
    x, y, width, height = [float(value) for value in annotation["bbox_xywh"]]
    return [x, y, x + width, y + height]


def iou(box_a: list[float], box_b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    intersection_x1 = max(ax1, bx1)
    intersection_y1 = max(ay1, by1)
    intersection_x2 = min(ax2, bx2)
    intersection_y2 = min(ay2, by2)
    intersection_width = max(0.0, intersection_x2 - intersection_x1)
    intersection_height = max(0.0, intersection_y2 - intersection_y1)
    intersection_area = intersection_width * intersection_height
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - intersection_area
    if union <= 0:
        return 0.0
    return intersection_area / union


def match_image(gt_boxes: list[list[float]], predicted_boxes: list[list[float]], threshold: float) -> tuple[int, int, int, list[float]]:
    candidates = []
    for gt_index, gt_box in enumerate(gt_boxes):
        for pred_index, predicted_box in enumerate(predicted_boxes):
            overlap = iou(gt_box, predicted_box)
            if overlap >= threshold:
                candidates.append((overlap, gt_index, pred_index))

    candidates.sort(reverse=True)
    matched_gt = set()
    matched_pred = set()
    matched_ious = []
    for overlap, gt_index, pred_index in candidates:
        if gt_index in matched_gt or pred_index in matched_pred:
            continue
        matched_gt.add(gt_index)
        matched_pred.add(pred_index)
        matched_ious.append(overlap)

    true_positive = len(matched_ious)
    false_positive = len(predicted_boxes) - true_positive
    false_negative = len(gt_boxes) - true_positive
    return true_positive, false_positive, false_negative, matched_ious


def main() -> int:
    args = parse_args()
    manifest_rows = load_jsonl(args.manifest_jsonl)
    predictions_by_id = {row["image_id"]: row for row in load_jsonl(args.predictions_jsonl)}

    missing = [row["image_id"] for row in manifest_rows if row["image_id"] not in predictions_by_id]
    if missing:
        raise SystemExit(f"Missing predictions for {len(missing)} images: {missing[:5]}")

    true_positive = 0
    false_positive = 0
    false_negative = 0
    gt_box_count = 0
    predicted_box_count = 0
    positive_images = 0
    negative_images = 0
    positive_images_detected = 0
    negative_images_with_detection = 0
    matched_ious = []
    latencies = []

    for row in manifest_rows:
        gt_boxes = [annotation_xyxy(annotation) for annotation in row.get("annotations") or []]
        prediction = predictions_by_id[row["image_id"]]
        detections = [
            detection
            for detection in prediction.get("detections") or []
            if float(detection.get("score", 0.0)) >= args.score_threshold
            and str(detection.get("label", "fish")) == "fish"
        ]
        predicted_boxes = [[float(value) for value in detection["bbox_xyxy"]] for detection in detections]

        tp, fp, fn, image_ious = match_image(gt_boxes, predicted_boxes, args.iou_threshold)
        true_positive += tp
        false_positive += fp
        false_negative += fn
        gt_box_count += len(gt_boxes)
        predicted_box_count += len(predicted_boxes)
        matched_ious.extend(image_ious)

        if gt_boxes:
            positive_images += 1
            if tp > 0:
                positive_images_detected += 1
        else:
            negative_images += 1
            if predicted_boxes:
                negative_images_with_detection += 1

        if "latency_ms" in prediction:
            latencies.append(float(prediction["latency_ms"]))

    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    report = {
        "image_count": len(manifest_rows),
        "positive_image_count": positive_images,
        "negative_image_count": negative_images,
        "ground_truth_box_count": gt_box_count,
        "predicted_box_count": predicted_box_count,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "positive_image_recall": round(positive_images_detected / positive_images, 4) if positive_images else None,
        "negative_image_false_positive_rate": (
            round(negative_images_with_detection / negative_images, 4) if negative_images else None
        ),
        "mean_matched_iou": round(mean(matched_ious), 4) if matched_ious else None,
        "mean_latency_ms": round(mean(latencies), 2) if latencies else None,
        "score_threshold": args.score_threshold,
        "iou_threshold": args.iou_threshold,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
