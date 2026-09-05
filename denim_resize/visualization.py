from __future__ import annotations

import cv2
import numpy as np


def make_overlay(image_bgr: np.ndarray, mask: np.ndarray, alpha: float = 0.30) -> np.ndarray:
    if image_bgr.shape[:2] != mask.shape:
        raise ValueError("Image and mask shapes do not match")
    overlay = image_bgr.copy()
    tint = np.zeros_like(image_bgr)
    tint[..., 1] = 220
    overlay[mask] = cv2.addWeighted(
        image_bgr[mask], 1.0 - alpha, tint[mask], alpha, 0
    )
    contours, _ = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    cv2.drawContours(overlay, contours, -1, (0, 220, 255), 2, cv2.LINE_AA)
    return overlay


def extract_foreground(image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    if image_bgr.shape[:2] != mask.shape:
        raise ValueError("Image and mask shapes do not match")
    output = np.full_like(image_bgr, 255)
    output[mask] = image_bgr[mask]
    return output


def make_comparison(
    left_bgr: np.ndarray,
    right_bgr: np.ndarray,
    left_label: str,
    right_label: str,
) -> np.ndarray:
    panel_height = max(left_bgr.shape[0], right_bgr.shape[0])
    label_height = 52
    gap = 16
    panel_width = max(left_bgr.shape[1], right_bgr.shape[1])
    canvas = np.full(
        (panel_height + label_height, panel_width * 2 + gap, 3), 245, dtype=np.uint8
    )
    for index, (image, label) in enumerate(
        ((left_bgr, left_label), (right_bgr, right_label))
    ):
        x = index * (panel_width + gap) + (panel_width - image.shape[1]) // 2
        y = label_height + (panel_height - image.shape[0]) // 2
        canvas[y : y + image.shape[0], x : x + image.shape[1]] = image
        cv2.putText(
            canvas,
            label,
            (index * (panel_width + gap) + 16, 34),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.85,
            (35, 35, 35),
            2,
            cv2.LINE_AA,
        )
    return canvas


def make_size_series(
    images_bgr: list[np.ndarray], labels: list[str], gap: int = 18
) -> np.ndarray:
    if not images_bgr or len(images_bgr) != len(labels):
        raise ValueError("A non-empty label is required for every image")
    label_height = 54
    margin = 16
    panel_height = max(image.shape[0] for image in images_bgr)
    width = sum(image.shape[1] for image in images_bgr)
    width += gap * (len(images_bgr) - 1) + 2 * margin
    canvas = np.full((panel_height + label_height, width, 3), 245, dtype=np.uint8)
    cursor = margin
    for image, label in zip(images_bgr, labels, strict=True):
        y = label_height + (panel_height - image.shape[0]) // 2
        canvas[y : y + image.shape[0], cursor : cursor + image.shape[1]] = image
        cv2.putText(
            canvas,
            label,
            (cursor + 8, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.78,
            (35, 35, 35),
            2,
            cv2.LINE_AA,
        )
        cursor += image.shape[1] + gap
    return canvas
