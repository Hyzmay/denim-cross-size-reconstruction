import unittest

import cv2
import numpy as np

from denim_resize.canonical import build_canonical_garment
from denim_resize.details import detect_detail_constraints
from denim_resize.edge import EdgeRefinementConfig, refine_garment_edge
from denim_resize.matting import estimate_foreground_matte
from denim_resize.structure import infer_pants_structures


def _pants_mask() -> np.ndarray:
    mask = np.zeros((140, 100), dtype=np.uint8)
    polygon = np.array(
        [
            [24, 10],
            [76, 10],
            [80, 54],
            [64, 72],
            [68, 130],
            [52, 130],
            [50, 74],
            [48, 130],
            [32, 130],
            [36, 72],
            [20, 54],
        ],
        dtype=np.int32,
    )
    cv2.fillPoly(mask, [polygon], 1)
    return mask.astype(bool)


class EdgeDetailCanonicalTests(unittest.TestCase):
    def test_matte_recovers_antialiased_dark_foreground_without_white_fringe(self) -> None:
        alpha = np.zeros((80, 80), dtype=np.float32)
        cv2.rectangle(alpha, (18, 10), (62, 70), 1.0, cv2.FILLED)
        alpha = cv2.GaussianBlur(alpha, (0, 0), 1.0)
        foreground = np.full((80, 80, 3), (35, 40, 45), dtype=np.float32)
        image = foreground * alpha[..., None] + 255.0 * (1.0 - alpha[..., None])
        image = np.clip(image, 0, 255).astype(np.uint8)
        mask = alpha >= 0.5

        matte = estimate_foreground_matte(image, mask)
        transition = (matte.alpha > 0.05) & (matte.alpha < 0.95)

        self.assertGreater(np.count_nonzero(transition), 0)
        self.assertLess(float(np.mean(matte.foreground_bgr[transition])), 80.0)
        self.assertLessEqual(matte.metrics["recomposition_mae"], 2.0)

    def test_edge_refinement_reduces_jagged_boundary_without_geometry_drift(self) -> None:
        mask = np.zeros((100, 100), dtype=bool)
        mask[10:90, 20:80] = True
        mask[12:88:2, 20] = False
        image = np.full((100, 100, 3), 255, dtype=np.uint8)
        image[mask] = (45, 50, 55)
        result = refine_garment_edge(
            image,
            mask,
            EdgeRefinementConfig(maximum_area_change_fraction=0.02),
        )
        self.assertLessEqual(result.metrics["area_change_fraction"], 0.02)
        self.assertLessEqual(
            result.metrics["roughness_after"], result.metrics["roughness_before"]
        )
        self.assertGreater(result.metrics["antialias_transition_pixels"], 0)

    def test_edge_refinement_uses_warped_alpha_hint(self) -> None:
        mask = np.zeros((60, 60), dtype=bool)
        mask[10:50, 15:45] = True
        image = np.full((60, 60, 3), 255, dtype=np.uint8)
        image[mask] = (40, 45, 50)
        alpha_hint = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 1.0)
        result = refine_garment_edge(image, mask, alpha_hint=alpha_hint)
        self.assertTrue(result.metrics["alpha_hint_used"])
        self.assertGreater(result.metrics["antialias_transition_pixels"], 0)

    def test_detail_detector_protects_a_strong_internal_seam(self) -> None:
        mask = np.zeros((100, 100), dtype=bool)
        mask[10:90, 15:85] = True
        image = np.full((100, 100, 3), 255, dtype=np.uint8)
        image[mask] = (45, 45, 45)
        cv2.line(image, (50, 15), (50, 85), (210, 210, 210), 3)
        details = detect_detail_constraints(image, mask)
        self.assertGreater(np.count_nonzero(details.seam_mask[:, 48:53]), 40)
        self.assertTrue(np.all(details.protected_mask[details.seam_mask]))

    def test_canonical_map_covers_mask_and_separates_left_right_regions(self) -> None:
        mask = _pants_mask()
        structures = infer_pants_structures(mask)
        canonical = build_canonical_garment(mask, structures)
        self.assertEqual(canonical.metrics["coverage"], 1.0)
        self.assertTrue(np.all(canonical.uv[mask] >= -1.0))
        self.assertTrue(np.all(canonical.uv[mask] <= 1.0))
        labels = set(np.unique(canonical.regions[mask]).tolist())
        self.assertTrue({1, 2, 3, 4, 5, 6, 7, 8, 9, 10}.issubset(labels))


if __name__ == "__main__":
    unittest.main()
