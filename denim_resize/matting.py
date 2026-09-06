from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np
from scipy import ndimage


@dataclass(frozen=True, slots=True)
class MattingConfig:
    unknown_radius: int = 3
    minimum_alpha_for_decontamination: float = 0.05
    color_separation_floor: float = 12.0

    def __post_init__(self) -> None:
        if self.unknown_radius < 1:
            raise ValueError("unknown_radius must be at least 1")
        if not 0 < self.minimum_alpha_for_decontamination < 1:
            raise ValueError("minimum_alpha_for_decontamination must be in (0, 1)")
        if self.color_separation_floor <= 0:
            raise ValueError("color_separation_floor must be positive")

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(slots=True)
class ForegroundMatte:
    foreground_bgr: np.ndarray
    alpha: np.ndarray
    background_bgr: tuple[float, float, float]
    metrics: dict[str, float | int | bool | list[float] | str]


def _estimate_background_bgr(image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    band = max(1, round(min(height, width) * 0.04))
    border_mask = np.zeros_like(mask)
    border_mask[:band] = True
    border_mask[-band:] = True
    border_mask[:, :band] = True
    border_mask[:, -band:] = True
    candidates = image_bgr[border_mask & ~mask]
    if candidates.size == 0:
        candidates = image_bgr[~mask]
    if candidates.size == 0:
        raise ValueError("Cannot estimate a background color from a full-frame mask")
    return np.median(candidates.astype(np.float32), axis=0)


def estimate_foreground_matte(
    image_bgr: np.ndarray,
    mask: np.ndarray,
    config: MattingConfig | None = None,
) -> ForegroundMatte:
    config = config or MattingConfig()
    if image_bgr.shape[:2] != mask.shape:
        raise ValueError("Image and mask shapes must match")
    if image_bgr.dtype != np.uint8 or mask.dtype != bool:
        raise ValueError("image_bgr must be uint8 and mask must be boolean")
    if not np.any(mask):
        raise ValueError("Cannot estimate a matte for an empty mask")

    radius = config.unknown_radius
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1)
    )
    sure_foreground = cv2.erode(mask.astype(np.uint8), kernel).astype(bool)
    if not np.any(sure_foreground):
        sure_foreground = mask.copy()
    possible_foreground = cv2.dilate(mask.astype(np.uint8), kernel).astype(bool)
    unknown = possible_foreground & ~sure_foreground

    _, nearest = ndimage.distance_transform_edt(~sure_foreground, return_indices=True)
    foreground_reference = image_bgr[nearest[0], nearest[1]].astype(np.float32)
    observed = image_bgr.astype(np.float32)
    background = _estimate_background_bgr(image_bgr, mask)
    foreground_delta = foreground_reference - background
    observed_delta = observed - background
    denominator = np.sum(foreground_delta * foreground_delta, axis=2)
    numerator = np.sum(observed_delta * foreground_delta, axis=2)
    color_alpha = np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator),
        where=denominator > 1e-6,
    )
    color_alpha = np.clip(color_alpha, 0.0, 1.0)

    spatial_alpha = cv2.GaussianBlur(
        mask.astype(np.float32),
        (0, 0),
        sigmaX=max(radius / 2.0, 0.5),
        sigmaY=max(radius / 2.0, 0.5),
    )
    color_confident = denominator >= config.color_separation_floor**2
    alpha = np.zeros(mask.shape, dtype=np.float32)
    alpha[sure_foreground] = 1.0
    alpha[unknown] = np.where(
        color_confident[unknown], color_alpha[unknown], spatial_alpha[unknown]
    )
    alpha[~possible_foreground] = 0.0
    alpha = np.clip(alpha, 0.0, 1.0)

    safe_alpha = np.maximum(alpha, config.minimum_alpha_for_decontamination)
    decontaminated = (
        observed - (1.0 - alpha[..., None]) * background
    ) / safe_alpha[..., None]
    weak_alpha = alpha < config.minimum_alpha_for_decontamination
    decontaminated[weak_alpha] = foreground_reference[weak_alpha]
    decontaminated[sure_foreground] = observed[sure_foreground]
    foreground_bgr = np.clip(decontaminated, 0, 255).astype(np.uint8)

    recomposed = (
        foreground_bgr.astype(np.float32) * alpha[..., None]
        + background * (1.0 - alpha[..., None])
    )
    evaluated = unknown & (alpha > 0.01)
    recomposition_mae = (
        float(np.mean(np.abs(recomposed[evaluated] - observed[evaluated])))
        if np.any(evaluated)
        else 0.0
    )
    transition = (alpha > 0.01) & (alpha < 0.99)
    metrics: dict[str, float | int | bool | list[float] | str] = {
        "method": "color_projection_trimap",
        "background_bgr": [float(value) for value in background],
        "unknown_radius_px": radius,
        "unknown_area_px": int(np.count_nonzero(unknown)),
        "transition_area_px": int(np.count_nonzero(transition)),
        "recomposition_mae": recomposition_mae,
        "quality_scope": "source-boundary proxy without alpha ground truth",
        "acceptance_passed": recomposition_mae <= 2.0,
    }
    return ForegroundMatte(
        foreground_bgr=foreground_bgr,
        alpha=alpha,
        background_bgr=tuple(float(value) for value in background),
        metrics=metrics,
    )
