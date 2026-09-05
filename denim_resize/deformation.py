from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .edge import extend_foreground_color
from .sizes import GarmentMeasurements
from .structure import PantsStructure, row_runs


@dataclass(frozen=True, slots=True)
class DeformationRatios:
    waist: float
    hip: float
    knee: float
    length: float
    front_rise: float

    @classmethod
    def from_measurements(
        cls, source: GarmentMeasurements, target: GarmentMeasurements
    ) -> "DeformationRatios":
        return cls(
            waist=target.waist_cm / source.waist_cm,
            hip=target.hip_cm / source.hip_cm,
            knee=target.knee_cm / source.knee_cm,
            length=target.outseam_cm / source.outseam_cm,
            front_rise=target.front_rise_cm / source.front_rise_cm,
        )

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(slots=True)
class WarpedComponent:
    image: np.ndarray
    mask: np.ndarray
    new_region: np.ndarray
    displacement: np.ndarray
    local_scale: np.ndarray
    metrics: dict[str, object]


def _scaled_interval(
    start: int,
    end: int,
    source_center: float,
    target_center: float,
    scale: float,
) -> tuple[int, int]:
    left = round(target_center + (start - source_center) * scale)
    right = round(target_center + (end - source_center) * scale)
    return min(left, right), max(left, right)


def _map_y(
    target_y: int,
    source_height: int,
    source_crotch: int,
    target_height: int,
    target_crotch: int,
) -> float:
    if target_y <= target_crotch:
        return target_y * source_crotch / max(target_crotch, 1)
    return source_crotch + (
        (target_y - target_crotch)
        * (source_height - 1 - source_crotch)
        / max(target_height - 1 - target_crotch, 1)
    )


def warp_component(
    image_bgr: np.ndarray,
    mask: np.ndarray,
    structure: PantsStructure,
    ratios: DeformationRatios,
    background_bgr: tuple[int, int, int] = (255, 255, 255),
) -> WarpedComponent:
    x, y, width, height = structure.x, structure.y, structure.width, structure.height
    source_image = image_bgr[y : y + height, x : x + width]
    source_mask = mask[y : y + height, x : x + width]
    source_crotch = structure.crotch_y - y
    source_hip = structure.hip_y - y
    source_knee = structure.knee_y - y

    target_height = max(2, round(height * ratios.length))
    target_crotch = round(source_crotch * ratios.front_rise)
    target_crotch = int(np.clip(target_crotch, 1, target_height - 2))
    maximum_width_scale = max(ratios.waist, ratios.hip, ratios.knee)
    target_width = max(2, round(width * maximum_width_scale) + 4)
    source_center = (width - 1) / 2.0
    target_center = (target_width - 1) / 2.0

    map_x = np.full((target_height, target_width), -1.0, dtype=np.float32)
    map_y = np.full_like(map_x, -1.0)
    target_mask = np.zeros((target_height, target_width), dtype=bool)
    preserved_mask = np.zeros_like(target_mask)
    local_scale = np.zeros((target_height, target_width), dtype=np.float32)

    anchors_y = np.array(
        [0, source_hip, source_crotch, source_knee, height - 1], dtype=np.float32
    )
    anchors_scale = np.array(
        [ratios.waist, ratios.hip, ratios.hip, ratios.knee, ratios.knee],
        dtype=np.float32,
    )

    for target_y in range(target_height):
        source_y = _map_y(
            target_y, height, source_crotch, target_height, target_crotch
        )
        source_row = int(np.clip(round(source_y), 0, height - 1))
        horizontal_scale = float(np.interp(source_y, anchors_y, anchors_scale))
        runs = row_runs(source_mask[source_row])
        for start, end in runs:
            target_start, target_end = _scaled_interval(
                start, end, source_center, target_center, horizontal_scale
            )
            target_start = max(0, target_start)
            target_end = min(target_width - 1, target_end)
            if target_end < target_start:
                continue
            xs = np.arange(target_start, target_end + 1, dtype=np.float32)
            source_xs = start + (xs - target_start) * (end - start) / max(
                target_end - target_start, 1
            )
            map_x[target_y, target_start : target_end + 1] = source_xs
            map_y[target_y, target_start : target_end + 1] = source_y
            target_mask[target_y, target_start : target_end + 1] = True
            local_scale[target_y, target_start : target_end + 1] = horizontal_scale

            preserved_start, preserved_end = _scaled_interval(
                start, end, source_center, target_center, 1.0
            )
            preserved_start = max(target_start, preserved_start)
            preserved_end = min(target_end, preserved_end)
            if preserved_end >= preserved_start:
                preserved_mask[target_y, preserved_start : preserved_end + 1] = True

    extended_source = extend_foreground_color(source_image, source_mask)
    warped = cv2.remap(
        extended_source,
        map_x,
        map_y,
        interpolation=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=background_bgr,
    )
    output = np.full_like(warped, background_bgr)
    output[target_mask] = warped[target_mask]
    new_region = target_mask & ~preserved_mask

    grid_x, grid_y = np.meshgrid(
        np.arange(target_width, dtype=np.float32),
        np.arange(target_height, dtype=np.float32),
    )
    displacement = np.zeros((target_height, target_width, 2), dtype=np.float32)
    displacement[..., 0] = map_x - (grid_x - target_center + source_center)
    displacement[..., 1] = map_y - grid_y / max(ratios.length, 1e-6)
    displacement[~target_mask] = 0

    source_area = int(np.count_nonzero(source_mask))
    target_area = int(np.count_nonzero(target_mask))
    metrics: dict[str, object] = {
        "source_bbox_xywh": [x, y, width, height],
        "source_crotch_y_local": source_crotch,
        "target_crotch_y_local": target_crotch,
        "target_shape_hw": [target_height, target_width],
        "source_mask_area_px": source_area,
        "target_mask_area_px": target_area,
        "area_ratio": target_area / max(source_area, 1),
        "new_region_area_px": int(np.count_nonzero(new_region)),
        "new_region_fraction_of_target": float(
            np.count_nonzero(new_region) / max(target_area, 1)
        ),
    }
    return WarpedComponent(
        image=output,
        mask=target_mask,
        new_region=new_region,
        displacement=displacement,
        local_scale=local_scale,
        metrics=metrics,
    )


def compose_components(
    components: list[WarpedComponent], gap: int = 24, margin: int = 16
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if not components:
        raise ValueError("At least one component is required")
    height = max(component.image.shape[0] for component in components) + 2 * margin
    width = sum(component.image.shape[1] for component in components)
    width += gap * (len(components) - 1) + 2 * margin
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    mask = np.zeros((height, width), dtype=bool)
    new_region = np.zeros_like(mask)
    displacement = np.zeros((height, width, 2), dtype=np.float32)
    local_scale = np.zeros((height, width), dtype=np.float32)
    cursor = margin
    for component in components:
        h, w = component.image.shape[:2]
        top = margin + (height - 2 * margin - h) // 2
        region = np.s_[top : top + h, cursor : cursor + w]
        component_mask = component.mask
        image_region = image[region]
        image_region[component_mask] = component.image[component_mask]
        mask[region] = component_mask
        new_region[region] = component.new_region
        displacement[region] = component.displacement
        local_scale[region] = component.local_scale
        cursor += w + gap
    return image, mask, new_region, displacement, local_scale


def displacement_visualization(displacement: np.ndarray, mask: np.ndarray) -> np.ndarray:
    magnitude, angle = cv2.cartToPolar(displacement[..., 0], displacement[..., 1])
    hsv = np.zeros((*mask.shape, 3), dtype=np.uint8)
    hsv[..., 0] = np.mod(angle * 90.0 / np.pi, 180).astype(np.uint8)
    hsv[..., 1] = np.where(mask, 230, 0).astype(np.uint8)
    if np.any(mask):
        maximum = float(np.percentile(magnitude[mask], 99))
        hsv[..., 2] = np.clip(magnitude * 255.0 / max(maximum, 1e-6), 0, 255)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def scale_visualization(local_scale: np.ndarray, mask: np.ndarray) -> np.ndarray:
    normalized = np.zeros_like(local_scale, dtype=np.uint8)
    if np.any(mask):
        values = local_scale[mask]
        low, high = float(values.min()), float(values.max())
        normalized[mask] = np.clip(
            (values - low) * 255.0 / max(high - low, 1e-6), 0, 255
        ).astype(np.uint8)
    color = cv2.applyColorMap(normalized, cv2.COLORMAP_TURBO)
    color[~mask] = 255
    return color
