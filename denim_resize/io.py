from __future__ import annotations

import hashlib
from pathlib import Path

import cv2
import numpy as np


def read_bgr(path: str | Path) -> np.ndarray:
    image_path = Path(path)
    if not image_path.is_file():
        raise FileNotFoundError(f"Image does not exist: {image_path}")

    encoded = np.fromfile(image_path, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"OpenCV could not decode image: {image_path}")
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    elif image.shape[2] != 3:
        raise ValueError(f"Unsupported channel count in {image_path}: {image.shape}")
    return np.ascontiguousarray(image)


def read_binary_mask(path: str | Path, expected_shape: tuple[int, int]) -> np.ndarray:
    image_path = Path(path)
    encoded = np.fromfile(image_path, dtype=np.uint8)
    mask = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise ValueError(f"OpenCV could not decode mask: {image_path}")
    if mask.shape != expected_shape:
        raise ValueError(
            f"Mask shape {mask.shape} does not match image shape {expected_shape}"
        )
    return mask >= 128


def write_image(path: str | Path, image: np.ndarray) -> None:
    image_path = Path(path)
    image_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = image_path.suffix.lower() or ".png"
    success, encoded = cv2.imencode(suffix, image)
    if not success:
        raise ValueError(f"OpenCV could not encode image as {suffix}: {image_path}")
    encoded.tofile(image_path)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()

