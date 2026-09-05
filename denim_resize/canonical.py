from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .structure import PantsStructure, row_runs


REGION_NAMES = {
    0: "background",
    1: "waistband",
    2: "left_hip",
    3: "right_hip",
    4: "crotch",
    5: "left_thigh",
    6: "right_thigh",
    7: "left_knee_leg",
    8: "right_knee_leg",
    9: "left_hem",
    10: "right_hem",
}


@dataclass(slots=True)
class CanonicalGarment:
    uv: np.ndarray
    regions: np.ndarray
    metrics: dict[str, float | int]


def _canonical_v(local_y: int, structure: PantsStructure) -> float:
    anchors_y = np.array(
        [
            0,
            structure.hip_y - structure.y,
            structure.crotch_y - structure.y,
            structure.knee_y - structure.y,
            structure.height - 1,
        ],
        dtype=np.float32,
    )
    anchors_v = np.array([0.0, 0.22, 0.40, 0.68, 1.0], dtype=np.float32)
    return float(np.interp(local_y, anchors_y, anchors_v))


def build_canonical_garment(
    mask: np.ndarray, structures: list[PantsStructure]
) -> CanonicalGarment:
    if mask.dtype != bool or mask.ndim != 2:
        raise ValueError("mask must be a two-dimensional boolean array")
    uv = np.full((*mask.shape, 2), -1.0, dtype=np.float32)
    regions = np.zeros(mask.shape, dtype=np.uint8)
    assigned = np.zeros_like(mask)

    for structure in structures:
        crop = mask[
            structure.y : structure.y + structure.height,
            structure.x : structure.x + structure.width,
        ]
        crotch = structure.crotch_y - structure.y
        hip = structure.hip_y - structure.y
        knee = structure.knee_y - structure.y
        hem_start = max(knee + 1, round(structure.height * 0.92))
        waistband_end = max(1, round(structure.height * 0.08))
        for local_y in range(structure.height):
            runs = row_runs(crop[local_y])
            if not runs:
                continue
            canonical_v = _canonical_v(local_y, structure)
            for run_index, (start, end) in enumerate(runs):
                xs = np.arange(start, end + 1)
                if len(runs) == 1:
                    canonical_u = np.linspace(-1.0, 1.0, len(xs), dtype=np.float32)
                elif run_index == 0:
                    canonical_u = np.linspace(-1.0, -0.05, len(xs), dtype=np.float32)
                elif run_index == len(runs) - 1:
                    canonical_u = np.linspace(0.05, 1.0, len(xs), dtype=np.float32)
                else:
                    canonical_u = np.linspace(-0.05, 0.05, len(xs), dtype=np.float32)
                global_y = structure.y + local_y
                global_x = structure.x + xs
                uv[global_y, global_x, 0] = canonical_u
                uv[global_y, global_x, 1] = canonical_v
                assigned[global_y, global_x] = True

                if local_y <= waistband_end:
                    labels = np.full(len(xs), 1, dtype=np.uint8)
                elif local_y < hip:
                    labels = np.where(canonical_u < 0, 2, 3).astype(np.uint8)
                elif local_y <= crotch:
                    labels = np.full(len(xs), 4, dtype=np.uint8)
                elif local_y < knee:
                    labels = np.where(canonical_u < 0, 5, 6).astype(np.uint8)
                elif local_y < hem_start:
                    labels = np.where(canonical_u < 0, 7, 8).astype(np.uint8)
                else:
                    labels = np.where(canonical_u < 0, 9, 10).astype(np.uint8)
                regions[global_y, global_x] = labels

    coverage = float(np.count_nonzero(assigned & mask) / max(np.count_nonzero(mask), 1))
    return CanonicalGarment(
        uv=uv,
        regions=regions,
        metrics={
            "mask_area_px": int(np.count_nonzero(mask)),
            "assigned_area_px": int(np.count_nonzero(assigned & mask)),
            "coverage": coverage,
            "region_count": int(len(np.unique(regions[regions > 0]))),
        },
    )


def canonical_uv_visualization(canonical: CanonicalGarment) -> np.ndarray:
    valid = canonical.regions > 0
    hsv = np.zeros((*canonical.regions.shape, 3), dtype=np.uint8)
    hsv[..., 0] = np.clip((canonical.uv[..., 0] + 1.0) * 89.5, 0, 179).astype(np.uint8)
    hsv[..., 1] = np.where(valid, 220, 0).astype(np.uint8)
    hsv[..., 2] = np.where(
        valid, np.clip(80 + canonical.uv[..., 1] * 175, 0, 255), 255
    ).astype(np.uint8)
    output = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    output[~valid] = 255
    return output


def semantic_region_visualization(canonical: CanonicalGarment) -> np.ndarray:
    palette = np.array(
        [
            [255, 255, 255],
            [30, 210, 245],
            [70, 190, 70],
            [90, 150, 230],
            [220, 100, 40],
            [180, 80, 210],
            [220, 100, 180],
            [190, 180, 50],
            [220, 150, 40],
            [80, 80, 230],
            [180, 80, 80],
        ],
        dtype=np.uint8,
    )
    return palette[canonical.regions]
