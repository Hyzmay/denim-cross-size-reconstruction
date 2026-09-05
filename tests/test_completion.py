import unittest

import cv2
import numpy as np

from denim_resize.completion import TextureCompletionConfig, complete_texture_exemplar


class TextureCompletionTests(unittest.TestCase):
    def test_exemplar_completion_adds_real_texture_without_changing_donor(self) -> None:
        height, width = 100, 100
        target_mask = np.zeros((height, width), dtype=bool)
        target_mask[8:92, 8:92] = True
        new_region = np.zeros_like(target_mask)
        new_region[8:92, 8:24] = True
        new_region[8:92, 76:92] = True

        image = np.full((height, width, 3), 255, dtype=np.uint8)
        image[target_mask] = (60, 60, 60)
        y, x = np.indices((height, width))
        denim_texture = ((x * 7 + y * 11) % 29).astype(np.uint8)
        donor = target_mask & ~new_region
        image[donor, 0] = 48 + denim_texture[donor]
        image[donor, 1] = 52 + denim_texture[donor]
        image[donor, 2] = 58 + denim_texture[donor]

        config = TextureCompletionConfig(
            patch_size=7,
            patch_stride=3,
            descriptor_window=7,
            blur_sigma=1.5,
            blend_radius=3.0,
        )
        first = complete_texture_exemplar(image, target_mask, new_region, config)
        second = complete_texture_exemplar(image, target_mask, new_region, config)

        self.assertTrue(np.array_equal(first.image[donor], image[donor]))
        self.assertTrue(np.array_equal(first.image[~target_mask], image[~target_mask]))
        self.assertTrue(np.array_equal(first.image, second.image))
        self.assertGreater(
            float(
                np.mean(
                    np.abs(
                        first.image[new_region].astype(np.float32)
                        - image[new_region].astype(np.float32)
                    )
                )
            ),
            0.0,
        )
        self.assertGreaterEqual(first.metrics["completed_fraction"], 0.95)
        self.assertLessEqual(
            first.metrics["texture_gradient_gap_after"],
            first.metrics["texture_gradient_gap_before"],
        )

    def test_rejects_new_region_outside_target(self) -> None:
        image = np.zeros((20, 20, 3), dtype=np.uint8)
        target_mask = np.zeros((20, 20), dtype=bool)
        new_region = np.zeros((20, 20), dtype=bool)
        new_region[5, 5] = True
        with self.assertRaises(ValueError):
            complete_texture_exemplar(image, target_mask, new_region)

    def test_protected_new_region_is_not_modified(self) -> None:
        image = np.full((60, 60, 3), 255, dtype=np.uint8)
        target_mask = np.zeros((60, 60), dtype=bool)
        target_mask[5:55, 5:55] = True
        image[target_mask] = (55, 60, 65)
        new_region = np.zeros_like(target_mask)
        new_region[5:55, 5:18] = True
        protected = np.zeros_like(target_mask)
        protected[20:40, 5:18] = True
        result = complete_texture_exemplar(
            image,
            target_mask,
            new_region,
            TextureCompletionConfig(patch_size=5, descriptor_window=5),
            protected_mask=protected,
        )
        self.assertTrue(np.array_equal(result.image[protected], image[protected]))
        self.assertEqual(
            result.metrics["protected_new_region_area_px"],
            int(np.count_nonzero(new_region & protected)),
        )


if __name__ == "__main__":
    unittest.main()
