from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np


class SegmentationError(RuntimeError):
    """Raised when the baseline cannot produce a plausible pants mask."""


@dataclass(frozen=True, slots=True)
class SegmentationConfig:
    border_fraction: float = 0.08
    background_distance_floor: float = 10.0
    background_mad_multiplier: float = 4.0
    morphology_fraction: float = 0.01
    grabcut_iterations: int = 5
    use_grabcut: bool = True
    max_major_components: int = 2
    min_relative_component_area: float = 0.25
    min_foreground_area_ratio: float = 0.02
    max_foreground_area_ratio: float = 0.90
    random_seed: int = 0

    def validate(self) -> None:
        if not 0.01 <= self.border_fraction <= 0.25:
            raise ValueError("border_fraction must be between 0.01 and 0.25")
        if self.background_distance_floor <= 0:
            raise ValueError("background_distance_floor must be positive")
        if self.background_mad_multiplier <= 0:
            raise ValueError("background_mad_multiplier must be positive")
        if not 0 < self.morphology_fraction <= 0.1:
            raise ValueError("morphology_fraction must be in (0, 0.1]")
        if self.grabcut_iterations < 1:
            raise ValueError("grabcut_iterations must be at least 1")
        if self.max_major_components < 1:
            raise ValueError("max_major_components must be at least 1")
        if not 0 < self.min_relative_component_area <= 1:
            raise ValueError("min_relative_component_area must be in (0, 1]")
        if not 0 < self.min_foreground_area_ratio < self.max_foreground_area_ratio < 1:
            raise ValueError("foreground area limits must satisfy 0 < min < max < 1")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class SegmentationResult:
    mask: np.ndarray
    diagnostics: dict[str, float | int | str]


def _border_pixels(image: np.ndarray, fraction: float) -> np.ndarray:
    height, width = image.shape[:2]
    band = max(1, round(min(height, width) * fraction))
    return np.concatenate(
        (
            image[:band].reshape(-1, image.shape[2]),
            image[-band:].reshape(-1, image.shape[2]),
            image[:, :band].reshape(-1, image.shape[2]),
            image[:, -band:].reshape(-1, image.shape[2]),
        ),
        axis=0,
    )


def _odd_kernel_size(shape: tuple[int, int], fraction: float) -> int:
    size = max(3, round(min(shape) * fraction))
    return size if size % 2 == 1 else size + 1


def _major_components(
    mask: np.ndarray, max_components: int, min_relative_area: float
) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8
    )
    if count <= 1:
        return np.zeros_like(mask, dtype=bool)
    areas = stats[1:, cv2.CC_STAT_AREA]
    ordered_labels = 1 + np.argsort(areas)[::-1]
    largest_area = int(areas[ordered_labels[0] - 1])
    selected = [
        int(label)
        for label in ordered_labels[:max_components]
        if int(areas[label - 1]) >= largest_area * min_relative_area
    ]
    return np.isin(labels, selected)


def _clean_mask(
    mask: np.ndarray,
    kernel_size: int,
    max_components: int,
    min_relative_area: float,
) -> np.ndarray:
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
    )
    cleaned = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
    cleaned = _major_components(
        cleaned > 0, max_components, min_relative_area
    ).astype(np.uint8)

    # Do not refill external contours here. Filling can bridge the open space
    # between trouser legs and move the inferred crotch far below its real
    # location. Morphological closing already handles small internal pinholes.
    return cleaned > 0


def _background_distance(
    image_bgr: np.ndarray, config: SegmentationConfig
) -> tuple[np.ndarray, float]:
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    border = _border_pixels(lab, config.border_fraction)
    background = np.median(border, axis=0)
    border_distance = np.linalg.norm(border - background, axis=1)
    median_distance = float(np.median(border_distance))
    mad = float(np.median(np.abs(border_distance - median_distance)))
    robust_threshold = median_distance + config.background_mad_multiplier * 1.4826 * mad
    threshold = max(config.background_distance_floor, robust_threshold)
    distance = np.linalg.norm(lab - background, axis=2)
    return distance, float(threshold)


def _grabcut_refine(
    image_bgr: np.ndarray,
    initial_mask: np.ndarray,
    background_distance: np.ndarray,
    background_threshold: float,
    config: SegmentationConfig,
) -> np.ndarray:
    height, width = initial_mask.shape
    grabcut_mask = np.full((height, width), cv2.GC_PR_BGD, dtype=np.uint8)
    grabcut_mask[initial_mask] = cv2.GC_PR_FGD
    grabcut_mask[background_distance <= background_threshold * 0.65] = cv2.GC_BGD

    band = max(1, round(min(height, width) * config.border_fraction))
    grabcut_mask[:band] = cv2.GC_BGD
    grabcut_mask[-band:] = cv2.GC_BGD
    grabcut_mask[:, :band] = cv2.GC_BGD
    grabcut_mask[:, -band:] = cv2.GC_BGD

    kernel_size = _odd_kernel_size(initial_mask.shape, config.morphology_fraction)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    sure_foreground = cv2.erode(initial_mask.astype(np.uint8), kernel) > 0
    if not np.any(sure_foreground):
        y, x = np.unravel_index(np.argmax(background_distance), initial_mask.shape)
        sure_foreground[y, x] = True
    grabcut_mask[sure_foreground] = cv2.GC_FGD

    background_model = np.zeros((1, 65), dtype=np.float64)
    foreground_model = np.zeros((1, 65), dtype=np.float64)
    cv2.setRNGSeed(config.random_seed)
    try:
        cv2.grabCut(
            image_bgr,
            grabcut_mask,
            None,
            background_model,
            foreground_model,
            config.grabcut_iterations,
            cv2.GC_INIT_WITH_MASK,
        )
    except cv2.error as error:
        raise SegmentationError(f"GrabCut failed: {error}") from error
    return np.isin(grabcut_mask, (cv2.GC_FGD, cv2.GC_PR_FGD))


def segment_pants(
    image_bgr: np.ndarray, config: SegmentationConfig | None = None
) -> SegmentationResult:
    config = config or SegmentationConfig()
    config.validate()
    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        raise ValueError("image_bgr must have shape (height, width, 3)")
    if image_bgr.dtype != np.uint8:
        raise ValueError("image_bgr must use uint8 pixels")
    if min(image_bgr.shape[:2]) < 32:
        raise ValueError("image must be at least 32 pixels in each dimension")

    distance, threshold = _background_distance(image_bgr, config)
    kernel_size = _odd_kernel_size(image_bgr.shape[:2], config.morphology_fraction)
    initial = _clean_mask(
        distance > threshold,
        kernel_size,
        config.max_major_components,
        config.min_relative_component_area,
    )
    if not np.any(initial):
        raise SegmentationError(
            "No foreground survived background separation; inspect the background prior"
        )

    refined = (
        _grabcut_refine(image_bgr, initial, distance, threshold, config)
        if config.use_grabcut
        else initial
    )
    final_mask = _clean_mask(
        refined,
        kernel_size,
        config.max_major_components,
        config.min_relative_component_area,
    )
    area_ratio = float(np.mean(final_mask))
    if not config.min_foreground_area_ratio <= area_ratio <= config.max_foreground_area_ratio:
        raise SegmentationError(
            f"Implausible foreground area ratio {area_ratio:.4f}; expected "
            f"[{config.min_foreground_area_ratio}, {config.max_foreground_area_ratio}]"
        )

    diagnostics: dict[str, float | int | str] = {
        "method": "border_grabcut" if config.use_grabcut else "border",
        "background_distance_threshold": threshold,
        "morphology_kernel_size": kernel_size,
        "max_major_components": config.max_major_components,
        "min_relative_component_area": config.min_relative_component_area,
        "initial_foreground_area_ratio": float(np.mean(initial)),
        "foreground_area_ratio": area_ratio,
    }
    return SegmentationResult(mask=final_mask, diagnostics=diagnostics)
