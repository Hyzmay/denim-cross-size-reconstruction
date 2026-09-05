import unittest

import numpy as np

from denim_resize.metrics import boundary_f1, mask_dice, mask_iou


class MaskMetricTests(unittest.TestCase):
    def test_identical_masks_score_one(self) -> None:
        mask = np.zeros((32, 32), dtype=bool)
        mask[8:24, 10:22] = True
        self.assertEqual(mask_iou(mask, mask), 1.0)
        self.assertEqual(mask_dice(mask, mask), 1.0)
        self.assertEqual(boundary_f1(mask, mask), 1.0)

    def test_disjoint_masks_score_zero(self) -> None:
        first = np.zeros((32, 32), dtype=bool)
        second = np.zeros((32, 32), dtype=bool)
        first[4:10, 4:10] = True
        second[22:28, 22:28] = True
        self.assertEqual(mask_iou(first, second), 0.0)
        self.assertEqual(mask_dice(first, second), 0.0)
        self.assertEqual(boundary_f1(first, second, tolerance_pixels=1), 0.0)

    def test_shape_mismatch_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            mask_iou(np.zeros((2, 2)), np.zeros((3, 3)))


if __name__ == "__main__":
    unittest.main()

