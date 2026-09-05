from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = (
    ("sample_002_gugr", "MEDIUM BLUE"),
    ("sample_006_gugr_black", "BLACK"),
    ("sample_007_gugr_raw_indigo", "RAW INDIGO"),
    ("sample_008_gugr_offwhite", "OFF WHITE"),
)
SIZES = ("32", "33", "34", "36", "38")


def read_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not decode {path}")
    return image


def main() -> None:
    rows: list[list[np.ndarray]] = []
    for sample_id, _ in SAMPLES:
        run = ROOT / "runs" / f"{sample_id}-multisize-final"
        rows.append(
            [read_image(run / f"size_{size}" / "reconstructed.png") for size in SIZES]
        )

    cell_width = max(image.shape[1] for row in rows for image in row) + 32
    cell_height = max(image.shape[0] for row in rows for image in row) + 32
    top_header = 72
    row_label_height = 46
    canvas = np.full(
        (
            top_header + len(rows) * (row_label_height + cell_height),
            len(SIZES) * cell_width,
            3,
        ),
        245,
        dtype=np.uint8,
    )

    for column, size in enumerate(SIZES):
        label = f"SIZE {size}" + ("  SOURCE" if size == "34" else "")
        x = column * cell_width + 18
        cv2.putText(
            canvas,
            label,
            (x, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (28, 28, 28),
            2,
            cv2.LINE_AA,
        )

    for row_index, ((_, row_label), images) in enumerate(zip(SAMPLES, rows, strict=True)):
        row_top = top_header + row_index * (row_label_height + cell_height)
        cv2.putText(
            canvas,
            row_label,
            (18, row_top + 31),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.68,
            (42, 42, 42),
            2,
            cv2.LINE_AA,
        )
        image_top = row_top + row_label_height
        for column, image in enumerate(images):
            x = column * cell_width + (cell_width - image.shape[1]) // 2
            y = image_top + (cell_height - image.shape[0]) // 2
            canvas[y : y + image.shape[0], x : x + image.shape[1]] = image

    output = ROOT / "docs" / "phase0" / "all_samples_multisize_summary.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), canvas):
        raise ValueError(f"Could not write {output}")
    print(output)

    preview = cv2.resize(
        canvas,
        (canvas.shape[1] // 2, canvas.shape[0] // 2),
        interpolation=cv2.INTER_AREA,
    )
    preview_output = ROOT / "docs" / "phase0" / "all_samples_multisize_preview.png"
    if not cv2.imwrite(str(preview_output), preview):
        raise ValueError(f"Could not write {preview_output}")
    print(preview_output)


if __name__ == "__main__":
    main()
