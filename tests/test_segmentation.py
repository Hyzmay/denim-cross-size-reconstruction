import unittest

import cv2
import numpy as np

from denim_resize.metrics import mask_diagnostics, mask_iou
from denim_resize.segmentation import SegmentationConfig, segment_pants


def synthetic_jeans() -> tuple[np.ndarray, np.ndarray]:
    height, width = 256, 192
    image = np.full((height, width, 3), 245, dtype=np.uint8)
    mask = np.zeros((height, width), dtype=np.uint8)

    cv2.rectangle(mask, (40, 28), (152, 58), 255, cv2.FILLED)
    cv2.fillPoly(
        mask,
        [
            np.array(
                [
                    [43, 52],
                    [149, 52],
                    [142, 118],
                    [126, 226],
                    [91, 226],
                    [88, 116],
                    [66, 226],
                    [31, 226],
                    [48, 116],
                ],
                dtype=np.int32,
            )
        ],
        255,
    )
    garment = mask > 0
    image[garment] = (120, 70, 28)
    for y in range(36, 220, 8):
        line = np.zeros_like(mask)
        cv2.line(line, (35, y), (148, y + 28), 255, 1, cv2.LINE_AA)
        image[(line > 0) & garment] = (145, 92, 46)
    return image, garment


def synthetic_two_view_jeans() -> tuple[np.ndarray, np.ndarray]:
    first_image, first_mask = synthetic_jeans()
    second_image = cv2.flip(first_image, 1)
    second_mask = cv2.flip(first_mask.astype(np.uint8), 1) > 0
    canvas = np.full((256, 404, 3), 245, dtype=np.uint8)
    target = np.zeros((256, 404), dtype=bool)
    canvas[:, :192] = first_image
    canvas[:, 212:] = second_image
    target[:, :192] = first_mask
    target[:, 212:] = second_mask
    return canvas, target


class SegmentationTests(unittest.TestCase):
    def test_synthetic_jeans_meets_phase0_threshold(self) -> None:
        image, target = synthetic_jeans()
        result = segment_pants(image, SegmentationConfig())
        self.assertGreaterEqual(mask_iou(result.mask, target), 0.95)
        self.assertEqual(mask_diagnostics(result.mask)["component_count"], 1)

    def test_default_segmentation_is_deterministic(self) -> None:
        image, _ = synthetic_jeans()
        first = segment_pants(image).mask
        second = segment_pants(image).mask
        np.testing.assert_array_equal(first, second)

    def test_two_major_garment_views_are_retained(self) -> None:
        image, target = synthetic_two_view_jeans()
        result = segment_pants(image)
        diagnostics = mask_diagnostics(result.mask)
        self.assertEqual(diagnostics["component_count"], 2)
        self.assertGreaterEqual(mask_iou(result.mask, target), 0.95)

    def test_component_limit_can_select_one_view(self) -> None:
        image, _ = synthetic_two_view_jeans()
        result = segment_pants(image, SegmentationConfig(max_major_components=1))
        self.assertEqual(mask_diagnostics(result.mask)["component_count"], 1)

    def test_invalid_image_dtype_is_rejected(self) -> None:
        image, _ = synthetic_jeans()
        with self.assertRaises(ValueError):
            segment_pants(image.astype(np.float32))


if __name__ == "__main__":
    unittest.main()
