from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np
from scipy import ndimage


@dataclass(frozen=True, slots=True)
class EdgeRefinementConfig:
    contour_sigma: float = 1.0
    feather_sigma: float = 0.75
    morphology_radius: int = 1
    maximum_area_change_fraction: float = 0.015

    def __post_init__(self) -> None:
        if self.contour_sigma <= 0 or self.feather_sigma <= 0:
            raise ValueError("contour_sigma and feather_sigma must be positive")
        if self.morphology_radius < 0:
            raise ValueError("morphology_radius must be non-negative")
        if not 0 <= self.maximum_area_change_fraction <= 0.1:
            raise ValueError("maximum_area_change_fraction must be between 0 and 0.1")

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(slots=True)
class EdgeRefinementResult:
    image: np.ndarray
    mask: np.ndarray
    alpha: np.ndarray
    metrics: dict[str, float | int | bool]


def extend_foreground_color(image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    if image_bgr.shape[:2] != mask.shape:
        raise ValueError("Image and mask shapes must match")
    if not np.any(mask):
        raise ValueError("Cannot extend an empty foreground mask")
    _, nearest = ndimage.distance_transform_edt(~mask, return_indices=True)
    extended = image_bgr.copy()
    extended[~mask] = image_bgr[nearest[0][~mask], nearest[1][~mask]]
    return extended


def contour_roughness(mask: np.ndarray) -> float:
    binary = mask.astype(np.uint8)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    area = float(np.count_nonzero(mask))
    if area == 0:
        return 0.0
    perimeter = sum(cv2.arcLength(contour, True) for contour in contours)
    return float(perimeter / np.sqrt(area))


def refine_garment_edge(
    image_bgr: np.ndarray,
    mask: np.ndarray,
    config: EdgeRefinementConfig | None = None,
    background_bgr: tuple[int, int, int] = (255, 255, 255),
) -> EdgeRefinementResult:
    config = config or EdgeRefinementConfig()
    if image_bgr.shape[:2] != mask.shape:
        raise ValueError("Image and mask shapes must match")
    if mask.dtype != bool:
        raise ValueError("mask must be a boolean array")
    if not np.any(mask):
        raise ValueError("Cannot refine an empty garment mask")

    binary = mask.astype(np.uint8)
    if config.morphology_radius:
        diameter = config.morphology_radius * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (diameter, diameter))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    smoothed = cv2.GaussianBlur(
        binary.astype(np.float32),
        (0, 0),
        sigmaX=config.contour_sigma,
        sigmaY=config.contour_sigma,
    )
    refined_mask = smoothed >= 0.5

    original_area = int(np.count_nonzero(mask))
    refined_area = int(np.count_nonzero(refined_mask))
    area_change_fraction = abs(refined_area - original_area) / max(original_area, 1)
    if area_change_fraction > config.maximum_area_change_fraction:
        refined_mask = mask.copy()
        refined_area = original_area
        area_change_fraction = 0.0

    extended = extend_foreground_color(image_bgr, mask).astype(np.float32)
    alpha = cv2.GaussianBlur(
        refined_mask.astype(np.float32),
        (0, 0),
        sigmaX=config.feather_sigma,
        sigmaY=config.feather_sigma,
    )
    alpha = np.clip(alpha, 0.0, 1.0)
    background = np.asarray(background_bgr, dtype=np.float32)
    output = extended * alpha[..., None] + background * (1.0 - alpha[..., None])
    output = np.clip(output, 0, 255).astype(np.uint8)

    roughness_before = contour_roughness(mask)
    roughness_after = contour_roughness(refined_mask)
    transitional_pixels = int(np.count_nonzero((alpha > 0.01) & (alpha < 0.99)))
    metrics: dict[str, float | int | bool] = {
        "original_mask_area_px": original_area,
        "refined_mask_area_px": refined_area,
        "area_change_fraction": float(area_change_fraction),
        "changed_mask_pixels": int(np.count_nonzero(mask ^ refined_mask)),
        "roughness_before": roughness_before,
        "roughness_after": roughness_after,
        "roughness_improvement": roughness_before - roughness_after,
        "antialias_transition_pixels": transitional_pixels,
        "acceptance_passed": (
            area_change_fraction <= config.maximum_area_change_fraction
            and roughness_after <= roughness_before + 1e-6
            and transitional_pixels > 0
        ),
    }
    return EdgeRefinementResult(
        image=output,
        mask=refined_mask,
        alpha=alpha,
        metrics=metrics,
    )
