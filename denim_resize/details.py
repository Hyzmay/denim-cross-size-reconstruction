from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(slots=True)
class DetailConstraints:
    seam_mask: np.ndarray
    silhouette_edge_mask: np.ndarray
    protected_mask: np.ndarray
    metrics: dict[str, float | int]


def _remove_small_components(mask: np.ndarray, minimum_area: int) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8
    )
    output = np.zeros_like(mask)
    for label in range(1, count):
        if stats[label, cv2.CC_STAT_AREA] >= minimum_area:
            output[labels == label] = True
    return output


def detect_detail_constraints(
    image_bgr: np.ndarray,
    garment_mask: np.ndarray,
) -> DetailConstraints:
    if image_bgr.shape[:2] != garment_mask.shape:
        raise ValueError("Image and garment mask shapes must match")
    if garment_mask.dtype != bool:
        raise ValueError("garment_mask must be a boolean array")
    if not np.any(garment_mask):
        raise ValueError("Cannot detect details in an empty garment mask")

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    smooth = cv2.GaussianBlur(gray, (0, 0), sigmaX=1.8, sigmaY=1.8)
    gradient_x = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(gradient_x, gradient_y)
    interior = cv2.erode(
        garment_mask.astype(np.uint8), np.ones((5, 5), dtype=np.uint8)
    ).astype(bool)
    threshold = float(np.percentile(magnitude[interior], 88.0)) if np.any(interior) else 0.0
    strong = (magnitude >= max(threshold, 8.0)) & interior
    strong = cv2.morphologyEx(
        strong.astype(np.uint8),
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
    ).astype(bool)
    minimum_area = max(6, round(np.count_nonzero(garment_mask) * 0.00003))
    seam_mask = _remove_small_components(strong, minimum_area)
    seam_mask = cv2.dilate(
        seam_mask.astype(np.uint8),
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
    ).astype(bool)

    silhouette_edge = cv2.morphologyEx(
        garment_mask.astype(np.uint8),
        cv2.MORPH_GRADIENT,
        np.ones((3, 3), dtype=np.uint8),
    ).astype(bool)
    protected = seam_mask | cv2.dilate(
        silhouette_edge.astype(np.uint8), np.ones((3, 3), dtype=np.uint8)
    ).astype(bool)
    garment_area = max(int(np.count_nonzero(garment_mask)), 1)
    metrics: dict[str, float | int] = {
        "gradient_threshold": threshold,
        "seam_pixels": int(np.count_nonzero(seam_mask)),
        "silhouette_edge_pixels": int(np.count_nonzero(silhouette_edge)),
        "protected_pixels": int(np.count_nonzero(protected & garment_mask)),
        "protected_fraction_of_garment": float(
            np.count_nonzero(protected & garment_mask) / garment_area
        ),
    }
    return DetailConstraints(
        seam_mask=seam_mask,
        silhouette_edge_mask=silhouette_edge,
        protected_mask=protected,
        metrics=metrics,
    )


def detail_visualization(
    image_bgr: np.ndarray, constraints: DetailConstraints
) -> np.ndarray:
    output = image_bgr.copy()
    seam_color = np.full_like(output, (0, 210, 255))
    edge_color = np.full_like(output, (255, 80, 20))
    output[constraints.seam_mask] = cv2.addWeighted(
        output[constraints.seam_mask],
        0.35,
        seam_color[constraints.seam_mask],
        0.65,
        0,
    )
    output[constraints.silhouette_edge_mask] = cv2.addWeighted(
        output[constraints.silhouette_edge_mask],
        0.35,
        edge_color[constraints.silhouette_edge_mask],
        0.65,
        0,
    )
    return output
