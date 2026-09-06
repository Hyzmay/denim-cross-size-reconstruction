from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .canonical import REGION_NAMES, CanonicalGarment
from .deformation import DeformationRatios, WarpedComponent
from .sizes import GarmentMeasurements


@dataclass(frozen=True, slots=True)
class TargetGeometry:
    """Machine-readable target geometry contract for the current baseline."""

    coordinate_frame: str
    source_view: str
    output_view: str
    landmarks: dict[str, dict[str, list[float]]]
    structure_curves: dict[str, dict[str, list[list[float]]]]
    silhouette: dict[str, object]
    semantic_regions: list[str]
    mesh: dict[str, object]
    measurement_constraints: dict[str, object]
    confidence: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _as_float_point(x: float, y: float) -> list[float]:
    return [float(x), float(y)]


def _target_anchor_metrics(component: WarpedComponent) -> dict[str, int]:
    metrics = component.metrics
    required = ("target_hip_y_local", "target_crotch_y_local", "target_knee_y_local")
    missing = [name for name in required if name not in metrics]
    if missing:
        raise ValueError(f"Warped component is missing target anchors: {missing}")
    return {
        "waist": 0,
        "hip": int(metrics["target_hip_y_local"]),
        "crotch": int(metrics["target_crotch_y_local"]),
        "knee": int(metrics["target_knee_y_local"]),
        "hem": int(component.mask.shape[0] - 1),
    }


def _silhouette_summary(target_mask: np.ndarray) -> dict[str, object]:
    if target_mask.dtype != bool or target_mask.ndim != 2:
        raise ValueError("target_mask must be a two-dimensional boolean array")
    area = int(np.count_nonzero(target_mask))
    if area == 0:
        return {"area_px": 0, "bbox_xywh": None, "contours": []}
    ys, xs = np.nonzero(target_mask)
    binary = target_mask.astype(np.uint8)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour_payload: list[list[list[float]]] = []
    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        epsilon = max(0.5, perimeter * 0.002)
        simplified = cv2.approxPolyDP(contour, epsilon, True)
        contour_payload.append(
            [[float(point[0][0]), float(point[0][1])] for point in simplified]
        )
    return {
        "area_px": area,
        "bbox_xywh": [
            int(xs.min()),
            int(ys.min()),
            int(xs.max() - xs.min() + 1),
            int(ys.max() - ys.min() + 1),
        ],
        "contours": contour_payload,
    }


def build_target_geometry(
    target_mask: np.ndarray,
    canonical: CanonicalGarment,
    components: list[WarpedComponent],
    source_measurements: GarmentMeasurements,
    target_measurements: GarmentMeasurements,
    ratios: DeformationRatios,
    view: str = "unspecified",
    gap: int = 24,
    margin: int = 16,
) -> TargetGeometry:
    """Build the explicit target representation used by this baseline.

    The structure anchors are heuristic mask-derived landmarks. They are a
    contract for later mesh/TPS work, not physical pattern ground truth.
    """
    if canonical.regions.ndim != 2:
        raise ValueError("canonical regions must be a two-dimensional array")
    if not components:
        raise ValueError("At least one warped component is required")

    output_height = max(component.mask.shape[0] for component in components) + 2 * margin
    landmarks: dict[str, dict[str, list[float]]] = {}
    structure_curves: dict[str, dict[str, list[list[float]]]] = {}
    cursor = margin
    for index, component in enumerate(components, start=1):
        height, width = component.mask.shape
        top = margin + (output_height - 2 * margin - height) // 2
        ys, xs = np.nonzero(component.mask)
        if len(xs) == 0:
            raise ValueError(f"Warped component {index} has an empty target mask")
        x0 = cursor + int(xs.min())
        x1 = cursor + int(xs.max())
        y0 = top + int(ys.min())
        y1 = top + int(ys.max())
        center_x = (x0 + x1) / 2.0
        anchors = _target_anchor_metrics(component)
        component_landmarks: dict[str, list[float]] = {}
        component_curves: dict[str, list[list[float]]] = {}
        for name, local_y in anchors.items():
            y = float(top + local_y)
            component_landmarks[name] = _as_float_point(center_x, y)
            component_curves[name] = [
                _as_float_point(x0, y),
                _as_float_point(x1, y),
            ]
        landmarks[f"component_{index}"] = component_landmarks
        structure_curves[f"component_{index}"] = component_curves
        cursor += width + gap

    semantic_labels = sorted(
        REGION_NAMES[int(label)]
        for label in np.unique(canonical.regions)
        if int(label) in REGION_NAMES and int(label) != 0
    )
    return TargetGeometry(
        coordinate_frame="target_image_pixels",
        source_view=view,
        output_view=view,
        landmarks=landmarks,
        structure_curves=structure_curves,
        silhouette=_silhouette_summary(target_mask),
        semantic_regions=semantic_labels,
        mesh={
            "available": False,
            "method": "row-wise remap baseline",
            "status": "scaffold_only",
        },
        measurement_constraints={
            "source": source_measurements.to_dict(),
            "target": target_measurements.to_dict(),
            "ratios": ratios.to_dict(),
            "physical_ground_truth": False,
            "status": "not_evaluated",
        },
        confidence={
            "landmarks": "heuristic_from_mask",
            "silhouette": "segmentation_proxy",
            "measurements": "merchant_chart",
            "physical_geometry": "not_evaluated",
        },
    )
