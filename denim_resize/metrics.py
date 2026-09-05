from __future__ import annotations

import cv2
import numpy as np


def _validate_pair(predicted: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    predicted_bool = np.asarray(predicted, dtype=bool)
    target_bool = np.asarray(target, dtype=bool)
    if predicted_bool.shape != target_bool.shape:
        raise ValueError(
            f"Mask shapes do not match: {predicted_bool.shape} vs {target_bool.shape}"
        )
    if predicted_bool.ndim != 2:
        raise ValueError("Masks must be two-dimensional")
    return predicted_bool, target_bool


def mask_iou(predicted: np.ndarray, target: np.ndarray) -> float:
    predicted_bool, target_bool = _validate_pair(predicted, target)
    union = np.count_nonzero(predicted_bool | target_bool)
    if union == 0:
        return 1.0
    return float(np.count_nonzero(predicted_bool & target_bool) / union)


def mask_dice(predicted: np.ndarray, target: np.ndarray) -> float:
    predicted_bool, target_bool = _validate_pair(predicted, target)
    denominator = np.count_nonzero(predicted_bool) + np.count_nonzero(target_bool)
    if denominator == 0:
        return 1.0
    return float(2 * np.count_nonzero(predicted_bool & target_bool) / denominator)


def _boundary(mask: np.ndarray) -> np.ndarray:
    kernel = np.ones((3, 3), dtype=np.uint8)
    mask_u8 = mask.astype(np.uint8)
    return cv2.morphologyEx(mask_u8, cv2.MORPH_GRADIENT, kernel) > 0


def boundary_f1(
    predicted: np.ndarray, target: np.ndarray, tolerance_pixels: float = 2.0
) -> float:
    if tolerance_pixels < 0:
        raise ValueError("tolerance_pixels must be non-negative")
    predicted_bool, target_bool = _validate_pair(predicted, target)
    predicted_boundary = _boundary(predicted_bool)
    target_boundary = _boundary(target_bool)
    predicted_count = np.count_nonzero(predicted_boundary)
    target_count = np.count_nonzero(target_boundary)
    if predicted_count == 0 and target_count == 0:
        return 1.0
    if predicted_count == 0 or target_count == 0:
        return 0.0

    distance_to_target = cv2.distanceTransform(
        (~target_boundary).astype(np.uint8), cv2.DIST_L2, 3
    )
    distance_to_predicted = cv2.distanceTransform(
        (~predicted_boundary).astype(np.uint8), cv2.DIST_L2, 3
    )
    precision = float(
        np.count_nonzero(distance_to_target[predicted_boundary] <= tolerance_pixels)
        / predicted_count
    )
    recall = float(
        np.count_nonzero(distance_to_predicted[target_boundary] <= tolerance_pixels)
        / target_count
    )
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def mask_diagnostics(mask: np.ndarray) -> dict[str, object]:
    mask_bool = np.asarray(mask, dtype=bool)
    if mask_bool.ndim != 2:
        raise ValueError("Mask must be two-dimensional")
    count, _, stats, _ = cv2.connectedComponentsWithStats(
        mask_bool.astype(np.uint8), connectivity=8
    )
    components = count - 1
    border = np.concatenate(
        (mask_bool[0], mask_bool[-1], mask_bool[:, 0], mask_bool[:, -1])
    )
    foreground_pixels = int(np.count_nonzero(mask_bool))
    bbox: list[int] | None = None
    if foreground_pixels:
        ys, xs = np.nonzero(mask_bool)
        bbox = [
            int(xs.min()),
            int(ys.min()),
            int(xs.max() - xs.min() + 1),
            int(ys.max() - ys.min() + 1),
        ]
    return {
        "foreground_pixels": foreground_pixels,
        "foreground_area_ratio": float(np.mean(mask_bool)),
        "component_count": int(components),
        "foreground_border_pixel_count": int(np.count_nonzero(border)),
        "bbox_xywh": bbox,
        "component_areas": [int(value) for value in stats[1:, cv2.CC_STAT_AREA]],
    }

