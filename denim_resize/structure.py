from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np


@dataclass(frozen=True, slots=True)
class PantsStructure:
    component_id: int
    x: int
    y: int
    width: int
    height: int
    top_y: int
    hip_y: int
    crotch_y: int
    knee_y: int
    hem_y: int
    center_x: float

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def row_runs(row: np.ndarray, minimum_length: int = 1) -> list[tuple[int, int]]:
    padded = np.pad(row.astype(np.int8), (1, 1))
    transitions = np.diff(padded)
    starts = np.flatnonzero(transitions == 1)
    ends = np.flatnonzero(transitions == -1) - 1
    return [
        (int(start), int(end))
        for start, end in zip(starts, ends, strict=True)
        if end - start + 1 >= minimum_length
    ]


def _detect_crotch(component: np.ndarray) -> int:
    height, width = component.shape
    start = max(1, round(height * 0.16))
    stop = min(height - 1, round(height * 0.68))
    minimum_run = max(2, round(width * 0.055))
    minimum_gap = max(2, round(width * 0.018))
    required = max(2, round(height * 0.012))

    consecutive = 0
    first = None
    for y in range(start, stop):
        runs = row_runs(component[y], minimum_run)
        split = (
            len(runs) >= 2
            and runs[-1][0] - runs[0][1] - 1 >= minimum_gap
        )
        if split:
            first = y if first is None else first
            consecutive += 1
            if consecutive >= required:
                return int(first)
        else:
            consecutive = 0
            first = None
    return round(height * 0.36)


def infer_pants_structures(mask: np.ndarray) -> list[PantsStructure]:
    binary = mask.astype(np.uint8)
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, 8)
    components: list[PantsStructure] = []
    order = sorted(range(1, count), key=lambda label: stats[label, cv2.CC_STAT_LEFT])
    for component_id, label in enumerate(order, start=1):
        x, y, width, height, area = stats[label]
        if area <= 0:
            continue
        crop = labels[y : y + height, x : x + width] == label
        crotch = _detect_crotch(crop)
        hip = min(crotch - 1, max(1, round(crotch * 0.52)))
        knee = min(height - 2, round(crotch + (height - 1 - crotch) * 0.52))
        components.append(
            PantsStructure(
                component_id=component_id,
                x=int(x),
                y=int(y),
                width=int(width),
                height=int(height),
                top_y=int(y),
                hip_y=int(y + hip),
                crotch_y=int(y + crotch),
                knee_y=int(y + knee),
                hem_y=int(y + height - 1),
                center_x=float(centroids[label, 0]),
            )
        )
    return components


def draw_structures(image_bgr: np.ndarray, structures: list[PantsStructure]) -> np.ndarray:
    output = image_bgr.copy()
    colors = {
        "waist": (0, 220, 255),
        "hip": (20, 190, 20),
        "crotch": (255, 120, 0),
        "knee": (180, 60, 255),
        "hem": (0, 60, 255),
    }
    for structure in structures:
        levels = (
            ("waist", structure.top_y),
            ("hip", structure.hip_y),
            ("crotch", structure.crotch_y),
            ("knee", structure.knee_y),
            ("hem", structure.hem_y),
        )
        for name, y in levels:
            cv2.line(
                output,
                (structure.x, y),
                (structure.x + structure.width - 1, y),
                colors[name],
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                output,
                name,
                (structure.x + 4, max(14, y - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                colors[name],
                1,
                cv2.LINE_AA,
            )
    return output
