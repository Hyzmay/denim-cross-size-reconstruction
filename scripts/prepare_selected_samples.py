from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SAMPLES_ROOT = ROOT / "data" / "raw" / "phase0" / "selected_samples"


def crop_browser_bars(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    useful_columns = np.flatnonzero(np.mean(gray > 35, axis=0) > 0.08)
    if useful_columns.size == 0:
        raise ValueError("No non-background image columns found")
    left, right = int(useful_columns[0]), int(useful_columns[-1]) + 1
    cropped = image[:, left:right]
    border_trim = min(24, cropped.shape[0] // 20, cropped.shape[1] // 20)
    return np.ascontiguousarray(
        cropped[border_trim:, border_trim : cropped.shape[1] - border_trim]
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_sheet(
    prepared_by_id: dict[str, np.ndarray], sample_ids: list[str], output_path: Path
) -> None:
    cell_width, cell_height = 560, 620
    rows = (len(sample_ids) + 1) // 2
    sheet = np.full((cell_height * rows, cell_width * 2, 3), 242, dtype=np.uint8)
    for index, sample_id in enumerate(sample_ids):
        image = prepared_by_id[sample_id]
        scale = min((cell_width - 30) / image.shape[1], (cell_height - 70) / image.shape[0])
        resized = cv2.resize(
            image,
            (round(image.shape[1] * scale), round(image.shape[0] * scale)),
            interpolation=cv2.INTER_AREA,
        )
        row, column = divmod(index, 2)
        x0, y0 = column * cell_width, row * cell_height
        x = x0 + (cell_width - resized.shape[1]) // 2
        y = y0 + 52 + (cell_height - 62 - resized.shape[0]) // 2
        sheet[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
        cv2.putText(
            sheet,
            sample_id,
            (x0 + 16, y0 + 34),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            (25, 25, 25),
            2,
            cv2.LINE_AA,
        )
    if not cv2.imwrite(str(output_path), sheet):
        raise ValueError(f"Could not write {output_path}")


def main() -> None:
    sample_directories = sorted(path for path in SAMPLES_ROOT.iterdir() if path.is_dir())
    records: list[dict[str, object]] = []
    prepared_by_id: dict[str, np.ndarray] = {}
    for sample_directory in sample_directories:
        raw_path = sample_directory / "source_raw.png"
        source_path = sample_directory / "source.png"
        input_path = raw_path if raw_path.is_file() else source_path
        image = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Could not decode {input_path}")
        cropped = crop_browser_bars(image)
        if not cv2.imwrite(str(source_path), cropped):
            raise ValueError(f"Could not write {source_path}")
        prepared_by_id[sample_directory.name] = cropped
        records.append(
            {
                "sample_id": sample_directory.name,
                "source_path": str(source_path.relative_to(ROOT)).replace("\\", "/"),
                "shape_hwc": list(cropped.shape),
                "sha256": sha256(source_path),
            }
        )

    write_sheet(
        prepared_by_id,
        [
            "sample_002_gugr",
            "sample_006_gugr_black",
            "sample_007_gugr_raw_indigo",
            "sample_008_gugr_offwhite",
        ],
        ROOT / "docs" / "phase0" / "selected_samples_primary.png",
    )
    write_sheet(
        prepared_by_id,
        ["sample_003_wassup", "sample_004_sdk", "sample_005_large_size"],
        ROOT / "docs" / "phase0" / "selected_samples_failure_set.png",
    )
    (SAMPLES_ROOT / "prepared_files.json").write_text(
        json.dumps({"samples": records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
