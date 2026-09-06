import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from denim_resize.io import write_image
from denim_resize.run import run_reconstruction, run_size_series
from denim_resize.segmentation import SegmentationConfig
from denim_resize.sizes import TAOBAO_612962220220
from denim_resize.structure import infer_pants_structures


def _synthetic_pants() -> tuple[np.ndarray, np.ndarray]:
    mask = np.zeros((180, 120), dtype=np.uint8)
    polygon = np.array(
        [
            [28, 12],
            [92, 12],
            [96, 58],
            [78, 92],
            [82, 166],
            [62, 166],
            [58, 94],
            [42, 166],
            [22, 166],
            [42, 92],
            [24, 58],
        ],
        dtype=np.int32,
    )
    cv2.fillPoly(mask, [polygon], 255)
    image = np.full((180, 120, 3), 248, dtype=np.uint8)
    image[mask > 0] = (130, 75, 35)
    for y in range(18, 165, 8):
        image[y : y + 2][mask[y : y + 2] > 0] = (160, 95, 55)
    return image, mask > 0


class ReconstructionTests(unittest.TestCase):
    def test_merchant_profile_is_item_specific(self) -> None:
        source, target = TAOBAO_612962220220.pair("32", "38")
        self.assertEqual(source.waist_cm, 81.0)
        self.assertEqual(target.hip_cm, 125.0)
        self.assertIn("612962220220", TAOBAO_612962220220.source_url)

    def test_structure_detects_crotch_and_levels(self) -> None:
        _, mask = _synthetic_pants()
        structures = infer_pants_structures(mask)
        self.assertEqual(len(structures), 1)
        structure = structures[0]
        self.assertLess(structure.hip_y, structure.crotch_y)
        self.assertLess(structure.crotch_y, structure.knee_y)
        self.assertLess(structure.knee_y, structure.hem_y)

    def test_full_reconstruction_writes_a_larger_target(self) -> None:
        image, _ = _synthetic_pants()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_path = root / "source.png"
            output_path = root / "run"
            write_image(source_path, image)
            result = run_reconstruction(
                source_path,
                output_path,
                source_size="32",
                target_size="38",
                view="front",
                segmentation_config=SegmentationConfig(
                    use_grabcut=False, max_major_components=1
                ),
            )
            self.assertGreater(result.metrics["measurement_ratios"]["waist"], 1.1)
            self.assertGreater(result.metrics["new_region_area_px"], 0)
            for filename in (
                "reconstructed.png",
                "reconstructed_baseline.png",
                "reconstructed_texture_completed.png",
                "comparison.png",
                "source_alpha.png",
                "source_foreground_matte.png",
                "target_mask.png",
                "refined_target_mask.png",
                "edge_alpha.png",
                "new_region_mask.png",
                "structure_landmarks.png",
                "canonical_uv.png",
                "semantic_regions.png",
                "canonical_representation.npz",
                "detail_protection_mask.png",
                "detail_constraints.png",
                "edge_refinement_comparison.png",
                "displacement_field.png",
                "local_scale_map.png",
                "texture_completion_regions.png",
                "texture_completion_comparison.png",
                "target_geometry.json",
                "config.json",
                "metrics.json",
                "manifest.json",
            ):
                self.assertTrue((output_path / filename).is_file(), filename)
            config = json.loads((output_path / "config.json").read_text("utf-8"))
            self.assertEqual(config["size_profile"]["item_id"], "612962220220")
            self.assertEqual(config["texture_completion"]["method"], "exemplar")
            self.assertGreaterEqual(
                result.metrics["texture_completion"]["completed_fraction"], 0.95
            )
            self.assertTrue(result.metrics["edge_refinement"]["acceptance_passed"])
            self.assertEqual(
                result.metrics["canonical_representation"]["coverage"], 1.0
            )
            self.assertIn("source_matting", result.metrics)
            self.assertFalse(result.metrics["physical_geometry_evaluated"])
            self.assertTrue(result.metrics["proxy_checks_passed"])
            self.assertFalse(result.metrics["geometry_evaluated"])
            self.assertEqual(result.metrics["physical_geometry_status"], "not_evaluated")
            target_geometry = json.loads(
                (output_path / "target_geometry.json").read_text("utf-8")
            )
            self.assertEqual(target_geometry["source_view"], "front")
            self.assertEqual(target_geometry["output_view"], "front")
            self.assertFalse(target_geometry["mesh"]["available"])

    def test_identity_size_preserves_mask_boundary_alpha_and_interior_pixels(self) -> None:
        image, _ = _synthetic_pants()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_path = root / "source.png"
            write_image(source_path, image)
            result = run_reconstruction(
                source_path,
                root / "identity",
                source_size="34",
                target_size="34",
                segmentation_config=SegmentationConfig(
                    use_grabcut=False, max_major_components=1
                ),
            )
            identity = result.metrics["identity_preservation"]
            self.assertTrue(identity["applicable"])
            self.assertTrue(identity["acceptance_passed"])
            self.assertGreaterEqual(identity["mask_iou"], 0.999)
            self.assertGreaterEqual(identity["boundary_f1_tolerance_1px"], 0.999)
            self.assertLessEqual(identity["interior_pixel_mae"], 0.5)

    def test_size_series_writes_all_targets_at_a_common_scale(self) -> None:
        image, _ = _synthetic_pants()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_path = root / "source.png"
            output_path = root / "series"
            write_image(source_path, image)
            result = run_size_series(
                source_path,
                output_path,
                source_size="34",
                target_sizes=["32", "34", "38"],
                segmentation_config=SegmentationConfig(
                    use_grabcut=False, max_major_components=1
                ),
            )
            self.assertTrue((output_path / "size_series.png").is_file())
            for size in ("32", "34", "38"):
                self.assertTrue(
                    (output_path / f"size_{size}" / "reconstructed.png").is_file()
                )
            self.assertEqual(result.metrics["target_sizes"], ["32", "34", "38"])
            self.assertTrue(result.metrics["proxy_checks_passed"])
            self.assertEqual(result.metrics["physical_geometry_status"], "not_evaluated")


if __name__ == "__main__":
    unittest.main()
