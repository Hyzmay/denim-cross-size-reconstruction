from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree


@dataclass(frozen=True, slots=True)
class TextureCompletionConfig:
    patch_size: int = 9
    patch_stride: int = 3
    descriptor_window: int = 11
    blur_sigma: float = 2.2
    blend_radius: float = 5.0
    max_donor_centers: int = 40_000

    def __post_init__(self) -> None:
        if self.patch_size < 3 or self.patch_size % 2 == 0:
            raise ValueError("patch_size must be an odd integer of at least 3")
        if self.patch_stride < 1:
            raise ValueError("patch_stride must be positive")
        if self.descriptor_window < 3 or self.descriptor_window % 2 == 0:
            raise ValueError("descriptor_window must be an odd integer of at least 3")
        if self.blur_sigma <= 0 or self.blend_radius <= 0:
            raise ValueError("blur_sigma and blend_radius must be positive")
        if self.max_donor_centers < 1:
            raise ValueError("max_donor_centers must be positive")

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(slots=True)
class TextureCompletionResult:
    image: np.ndarray
    donor_candidate_mask: np.ndarray
    donor_used_mask: np.ndarray
    completed_mask: np.ndarray
    metrics: dict[str, float | int | bool | str]


def _nearest_mask_fill(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    if np.all(mask):
        return image.astype(np.float32)
    _, indices = ndimage.distance_transform_edt(~mask, return_indices=True)
    filled = image.astype(np.float32).copy()
    filled[~mask] = image[indices[0][~mask], indices[1][~mask]]
    return filled


def _texture_features(image_float: np.ndarray, window: int) -> np.ndarray:
    image_u8 = np.clip(image_float, 0, 255).astype(np.uint8)
    lab = cv2.cvtColor(image_u8, cv2.COLOR_BGR2LAB).astype(np.float32)
    mean = cv2.boxFilter(lab, -1, (window, window), normalize=True)
    mean_square = cv2.boxFilter(lab * lab, -1, (window, window), normalize=True)
    standard_deviation = np.sqrt(np.maximum(mean_square - mean * mean, 0.0))

    gray = cv2.cvtColor(image_u8, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    gradient_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    height, width = gray.shape
    y_coordinate = np.broadcast_to(
        np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None], gray.shape
    )
    x_coordinate = np.broadcast_to(
        np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :], gray.shape
    )
    return np.concatenate(
        (
            mean / 255.0,
            standard_deviation / 64.0,
            np.abs(gradient_x)[..., None] / 4.0,
            np.abs(gradient_y)[..., None] / 4.0,
            (2.0 * y_coordinate)[..., None],
            (0.35 * x_coordinate)[..., None],
        ),
        axis=2,
    )


def _gradient_energy(image: np.ndarray, region: np.ndarray) -> float:
    if not np.any(region):
        return 0.0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gradient_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(gradient_x, gradient_y)
    return float(np.mean(magnitude[region]))


def complete_texture_exemplar(
    image_bgr: np.ndarray,
    target_mask: np.ndarray,
    new_region: np.ndarray,
    config: TextureCompletionConfig | None = None,
    protected_mask: np.ndarray | None = None,
) -> TextureCompletionResult:
    config = config or TextureCompletionConfig()
    if image_bgr.shape[:2] != target_mask.shape or target_mask.shape != new_region.shape:
        raise ValueError("Image, target mask, and new-region mask shapes must match")
    if target_mask.dtype != bool or new_region.dtype != bool:
        raise ValueError("target_mask and new_region must be boolean arrays")
    if np.any(new_region & ~target_mask):
        raise ValueError("new_region must be contained by target_mask")
    if protected_mask is None:
        protected_mask = np.zeros_like(target_mask)
    if protected_mask.shape != target_mask.shape or protected_mask.dtype != bool:
        raise ValueError("protected_mask must be a matching boolean array")

    baseline = image_bgr.copy()
    requested_new_area = int(np.count_nonzero(new_region))
    completion_region = new_region & ~protected_mask
    new_area = int(np.count_nonzero(completion_region))
    radius = config.patch_size // 2
    kernel = np.ones((config.patch_size, config.patch_size), dtype=np.uint8)
    protected_donor_band = cv2.dilate(
        protected_mask.astype(np.uint8), np.ones((3, 3), dtype=np.uint8)
    ).astype(bool)
    donor_mask = target_mask & ~new_region & ~protected_donor_band
    donor_candidates = cv2.erode(
        donor_mask.astype(np.uint8), kernel, iterations=1
    ).astype(bool)
    if not np.any(donor_candidates):
        donor_mask = target_mask & ~new_region
        donor_candidates = cv2.erode(
            donor_mask.astype(np.uint8), kernel, iterations=1
        ).astype(bool)
    donor_coordinates = np.argwhere(donor_candidates)
    if new_area == 0:
        return TextureCompletionResult(
            image=baseline,
            donor_candidate_mask=donor_candidates,
            donor_used_mask=np.zeros_like(target_mask),
            completed_mask=np.zeros_like(target_mask),
            metrics={
                "method": "exemplar_patch_vote",
                "new_region_area_px": requested_new_area,
                "protected_new_region_area_px": requested_new_area,
                "completion_region_area_px": 0,
                "completed_area_px": 0,
                "completed_fraction": 1.0,
                "donor_candidate_area_px": int(np.count_nonzero(donor_candidates)),
                "donor_used_area_px": 0,
                "texture_gradient_gap_before": 0.0,
                "texture_gradient_gap_after": 0.0,
                "acceptance_passed": True,
            },
        )
    if donor_coordinates.size == 0:
        raise ValueError("No valid donor patches remain after patch-size erosion")

    if len(donor_coordinates) > config.max_donor_centers:
        selection = np.linspace(
            0, len(donor_coordinates) - 1, config.max_donor_centers, dtype=np.int64
        )
        donor_coordinates = donor_coordinates[selection]

    filled = _nearest_mask_fill(baseline, target_mask)
    base = cv2.GaussianBlur(
        filled, (0, 0), sigmaX=config.blur_sigma, sigmaY=config.blur_sigma
    )
    residual = filled - base
    features = _texture_features(filled, config.descriptor_window)
    donor_features = features[donor_coordinates[:, 0], donor_coordinates[:, 1]]
    tree = cKDTree(donor_features)

    y_grid, x_grid = np.indices(target_mask.shape)
    sampled_targets = completion_region & (y_grid % config.patch_stride == 0)
    sampled_targets &= x_grid % config.patch_stride == 0
    target_coordinates = np.argwhere(sampled_targets)
    if target_coordinates.size == 0:
        target_coordinates = np.argwhere(completion_region)
    target_features = features[target_coordinates[:, 0], target_coordinates[:, 1]]
    _, nearest_indexes = tree.query(target_features, k=1)
    matched_donors = donor_coordinates[np.asarray(nearest_indexes)]

    axis = np.arange(-radius, radius + 1, dtype=np.float32)
    grid_x, grid_y = np.meshgrid(axis, axis)
    patch_weights = np.exp(
        -(grid_x * grid_x + grid_y * grid_y) / max(float(radius * radius), 1.0)
    ).astype(np.float32)
    residual_sum = np.zeros_like(filled, dtype=np.float32)
    weight_sum = np.zeros(target_mask.shape, dtype=np.float32)
    donor_used = np.zeros_like(target_mask)
    height, width = target_mask.shape

    for (target_y, target_x), (donor_y, donor_x) in zip(
        target_coordinates, matched_donors, strict=True
    ):
        target_y0 = max(0, int(target_y) - radius)
        target_y1 = min(height, int(target_y) + radius + 1)
        target_x0 = max(0, int(target_x) - radius)
        target_x1 = min(width, int(target_x) + radius + 1)
        patch_y0 = target_y0 - (int(target_y) - radius)
        patch_y1 = patch_y0 + (target_y1 - target_y0)
        patch_x0 = target_x0 - (int(target_x) - radius)
        patch_x1 = patch_x0 + (target_x1 - target_x0)
        donor_y0 = int(donor_y) - radius + patch_y0
        donor_y1 = int(donor_y) - radius + patch_y1
        donor_x0 = int(donor_x) - radius + patch_x0
        donor_x1 = int(donor_x) - radius + patch_x1

        region = np.s_[target_y0:target_y1, target_x0:target_x1]
        hole = completion_region[region]
        if not np.any(hole):
            continue
        weights = patch_weights[patch_y0:patch_y1, patch_x0:patch_x1] * hole
        donor_patch = residual[donor_y0:donor_y1, donor_x0:donor_x1]
        residual_sum[region] += donor_patch * weights[..., None]
        weight_sum[region] += weights
        donor_used[donor_y0:donor_y1, donor_x0:donor_x1] = True

    completed = completion_region & (weight_sum > 0)
    synthesized_residual = np.zeros_like(filled, dtype=np.float32)
    voted_residual = np.zeros_like(filled, dtype=np.float32)
    voted_residual[completed] = (
        residual_sum[completed] / weight_sum[completed, None]
    )

    _, nearest = ndimage.distance_transform_edt(
        ~donor_candidates, return_indices=True
    )
    coordinate_y, coordinate_x = np.indices(target_mask.shape)
    mirrored_y = np.clip(2 * nearest[0] - coordinate_y, 0, height - 1)
    mirrored_x = np.clip(2 * nearest[1] - coordinate_x, 0, width - 1)
    mirrored_valid = donor_candidates[mirrored_y, mirrored_x]
    source_y = np.where(mirrored_valid, mirrored_y, nearest[0])
    source_x = np.where(mirrored_valid, mirrored_x, nearest[1])
    coherent_residual = residual[source_y, source_x]
    synthesized_residual[completion_region] = coherent_residual[completion_region]
    synthesized_residual[completed] = (
        0.65 * coherent_residual[completed] + 0.35 * voted_residual[completed]
    )
    donor_used[source_y[completion_region], source_x[completion_region]] = True
    completed[completion_region] = True

    donor_rms = float(
        np.sqrt(np.mean(np.square(residual[donor_candidates]), dtype=np.float64))
    )
    synthesized_rms = float(
        np.sqrt(
            np.mean(
                np.square(synthesized_residual[completion_region]), dtype=np.float64
            )
        )
    )
    residual_gain = float(np.clip(donor_rms / max(synthesized_rms, 1e-6), 0.75, 2.0))
    synthesized_residual[completion_region] *= residual_gain

    synthesized = np.clip(base + synthesized_residual, 0, 255)
    distance_inside = cv2.distanceTransform(
        completion_region.astype(np.uint8), cv2.DIST_L2, 5
    )
    blend = np.clip((distance_inside - 1.0) / config.blend_radius, 0.0, 1.0)
    output_float = baseline.astype(np.float32)
    output_float[completion_region] = (
        baseline[completion_region].astype(np.float32)
        * (1.0 - blend[completion_region, None])
        + synthesized[completion_region] * blend[completion_region, None]
    )
    evaluation_interior = cv2.erode(
        target_mask.astype(np.uint8), np.ones((5, 5), dtype=np.uint8)
    ).astype(bool)
    evaluated_donor = donor_mask & evaluation_interior
    evaluated_new_region = completion_region & evaluation_interior
    if not np.any(evaluated_donor):
        evaluated_donor = donor_mask
    if not np.any(evaluated_new_region):
        evaluated_new_region = completion_region
    donor_energy = _gradient_energy(baseline, evaluated_donor)
    before_energy = _gradient_energy(baseline, evaluated_new_region)
    candidate = np.clip(output_float, 0, 255).astype(np.uint8)
    best_strength = 0.0
    output = baseline.copy()
    after_energy = before_energy
    best_gap = abs(before_energy - donor_energy)
    difference = candidate.astype(np.float32) - baseline.astype(np.float32)
    strengths = np.concatenate(
        (
            np.array([0.015625, 0.03125, 0.0625, 0.09375], dtype=np.float32),
            np.linspace(0.125, 1.0, 8, dtype=np.float32),
        )
    )
    for strength in strengths:
        calibrated = baseline.astype(np.float32)
        calibrated[completion_region] += difference[completion_region] * float(strength)
        calibrated_u8 = np.clip(calibrated, 0, 255).astype(np.uint8)
        energy = _gradient_energy(calibrated_u8, evaluated_new_region)
        gap = abs(energy - donor_energy)
        if gap < best_gap:
            best_strength = float(strength)
            best_gap = gap
            output = calibrated_u8
            after_energy = energy

    after_energy = _gradient_energy(output, evaluated_new_region)
    gap_before = abs(before_energy - donor_energy)
    gap_after = abs(after_energy - donor_energy)
    match_tolerance = max(1.0, donor_energy * 0.02)
    baseline_within_tolerance = gap_before <= match_tolerance
    completed_fraction = float(np.count_nonzero(completed) / max(new_area, 1))
    interface = completion_region & cv2.dilate(
        donor_mask.astype(np.uint8), np.ones((3, 3), dtype=np.uint8)
    ).astype(bool)
    interface_mae = (
        float(
            np.mean(
                np.abs(output[interface].astype(np.float32) - baseline[interface])
            )
        )
        if np.any(interface)
        else 0.0
    )
    metrics: dict[str, float | int | bool | str] = {
        "method": "exemplar_patch_vote",
        "new_region_area_px": requested_new_area,
        "protected_new_region_area_px": int(
            np.count_nonzero(new_region & protected_mask)
        ),
        "completion_region_area_px": new_area,
        "completed_area_px": int(np.count_nonzero(completed)),
        "completed_fraction": completed_fraction,
        "donor_candidate_area_px": int(np.count_nonzero(donor_candidates)),
        "donor_used_area_px": int(np.count_nonzero(donor_used)),
        "texture_evaluation_new_region_area_px": int(
            np.count_nonzero(evaluated_new_region)
        ),
        "donor_gradient_energy": donor_energy,
        "new_region_gradient_energy_before": before_energy,
        "new_region_gradient_energy_after": after_energy,
        "texture_gradient_gap_before": gap_before,
        "texture_gradient_gap_after": gap_after,
        "texture_gradient_match_tolerance": match_tolerance,
        "texture_transfer_strength": best_strength,
        "coherent_residual_gain": residual_gain,
        "candidate_gradient_energy": _gradient_energy(
            candidate, evaluated_new_region
        ),
        "baseline_within_texture_tolerance": baseline_within_tolerance,
        "completion_applied": best_strength > 0.0,
        "interface_mae_from_baseline": interface_mae,
        "acceptance_passed": (
            completed_fraction >= 0.95
            and gap_after <= gap_before
        ),
    }
    return TextureCompletionResult(
        image=output,
        donor_candidate_mask=donor_candidates,
        donor_used_mask=donor_used,
        completed_mask=completed,
        metrics=metrics,
    )


def completion_region_visualization(
    image_bgr: np.ndarray,
    new_region: np.ndarray,
    donor_candidate_mask: np.ndarray,
    donor_used_mask: np.ndarray,
) -> np.ndarray:
    visualization = image_bgr.copy()
    layers = (
        (donor_candidate_mask, np.array([40, 180, 40], dtype=np.uint8), 0.25),
        (donor_used_mask, np.array([220, 180, 20], dtype=np.uint8), 0.35),
        (new_region, np.array([30, 30, 240], dtype=np.uint8), 0.55),
    )
    for region, color, alpha in layers:
        if not np.any(region):
            continue
        color_layer = np.broadcast_to(color, visualization[region].shape)
        visualization[region] = cv2.addWeighted(
            visualization[region], 1.0 - alpha, color_layer, alpha, 0
        )
    return visualization
