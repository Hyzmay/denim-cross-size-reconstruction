from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_IDS = (
    "sample_002_gugr",
    "sample_006_gugr_black",
    "sample_007_gugr_raw_indigo",
    "sample_008_gugr_offwhite",
)


def read_image(path: Path, mode: int = cv2.IMREAD_COLOR) -> np.ndarray:
    image = cv2.imread(str(path), mode)
    if image is None:
        raise ValueError(f"Could not decode {path}")
    return image


def source_foreground(sample_id: str) -> np.ndarray:
    image = read_image(
        ROOT / "data" / "raw" / "phase0" / "selected_samples" / sample_id / "source.png"
    )
    mask = read_image(
        ROOT / "runs" / f"{sample_id}-segmentation" / "pants_mask.png",
        cv2.IMREAD_GRAYSCALE,
    )
    points = cv2.findNonZero((mask > 0).astype(np.uint8))
    if points is None:
        raise ValueError(f"Empty mask for {sample_id}")
    x, y, width, height = cv2.boundingRect(points)
    foreground = np.full((height, width, 3), 255, dtype=np.uint8)
    crop_mask = mask[y : y + height, x : x + width] > 0
    crop = image[y : y + height, x : x + width]
    foreground[crop_mask] = crop[crop_mask]
    return foreground


def place_centered(sheet: np.ndarray, image: np.ndarray, x0: int, y0: int) -> None:
    cell_width, cell_height = 500, 1120
    x = x0 + (cell_width - image.shape[1]) // 2
    content_top = 56
    y = y0 + content_top + (cell_height - content_top - image.shape[0]) // 2
    sheet[y : y + image.shape[0], x : x + image.shape[1]] = image


def main() -> None:
    cell_width, cell_height = 500, 1120
    header_height = 72
    sheet = np.full(
        (header_height + cell_height * len(SAMPLE_IDS), cell_width * 3, 3),
        245,
        dtype=np.uint8,
    )
    headings = ("TARGET 32 / SHRINK", "INPUT", "TARGET 38 / ENLARGE")
    for column, heading in enumerate(headings):
        cv2.putText(
            sheet,
            heading,
            (column * cell_width + 28, 46),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.76,
            (22, 22, 22),
            2,
            cv2.LINE_AA,
        )

    for row, sample_id in enumerate(SAMPLE_IDS):
        images = (
            read_image(ROOT / "runs" / f"{sample_id}-demo-38-to-32" / "reconstructed.png"),
            source_foreground(sample_id),
            read_image(
                ROOT
                / "runs"
                / f"{sample_id}-exemplar-32-to-38-final"
                / "reconstructed.png"
            ),
        )
        y0 = header_height + row * cell_height
        cv2.putText(
            sheet,
            sample_id,
            (18, y0 + 38),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.68,
            (35, 35, 35),
            2,
            cv2.LINE_AA,
        )
        for column, image in enumerate(images):
            place_centered(sheet, image, column * cell_width, y0)

    output = ROOT / "docs" / "phase0" / "selected_samples_resize_demo.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), sheet):
        raise ValueError(f"Could not write {output}")
    print(output)

    comparison_width, comparison_height = 900, 1060
    comparison_sheet = np.full(
        (comparison_height * 2, comparison_width * 2, 3), 245, dtype=np.uint8
    )
    for index, sample_id in enumerate(SAMPLE_IDS):
        comparison = read_image(
            ROOT
            / "runs"
            / f"{sample_id}-exemplar-32-to-38-final"
            / "texture_completion_comparison.png"
        )
        scale = min(
            (comparison_width - 24) / comparison.shape[1],
            (comparison_height - 62) / comparison.shape[0],
        )
        resized = cv2.resize(
            comparison,
            (round(comparison.shape[1] * scale), round(comparison.shape[0] * scale)),
            interpolation=cv2.INTER_AREA,
        )
        row, column = divmod(index, 2)
        x0, y0 = column * comparison_width, row * comparison_height
        x = x0 + (comparison_width - resized.shape[1]) // 2
        y = y0 + 48 + (comparison_height - 48 - resized.shape[0]) // 2
        comparison_sheet[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
        cv2.putText(
            comparison_sheet,
            sample_id,
            (x0 + 14, y0 + 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.68,
            (35, 35, 35),
            2,
            cv2.LINE_AA,
        )
    comparison_output = (
        ROOT / "docs" / "phase0" / "selected_samples_texture_completion.png"
    )
    if not cv2.imwrite(str(comparison_output), comparison_sheet):
        raise ValueError(f"Could not write {comparison_output}")
    print(comparison_output)


if __name__ == "__main__":
    main()
