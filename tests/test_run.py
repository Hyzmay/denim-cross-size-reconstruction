import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from denim_resize.io import write_image
from denim_resize.run import run_segmentation
from denim_resize.segmentation import SegmentationConfig


class RunTests(unittest.TestCase):
    def test_run_writes_artifacts_metrics_and_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            image = np.full((96, 96, 3), 245, dtype=np.uint8)
            target = np.zeros((96, 96), dtype=np.uint8)
            cv2.rectangle(target, (24, 12), (72, 84), 255, cv2.FILLED)
            image[target > 0] = (120, 70, 30)

            image_path = root / "source.png"
            target_path = root / "target.png"
            protocol_path = root / "protocol.md"
            output_path = root / "run"
            write_image(image_path, image)
            write_image(target_path, target)
            protocol_path.write_text("# Fixed before execution\n", encoding="utf-8")

            result = run_segmentation(
                image_path,
                output_path,
                config=SegmentationConfig(use_grabcut=False),
                ground_truth_path=target_path,
                protocol_path=protocol_path,
            )

            self.assertGreater(result.metrics["iou"], 0.95)
            for filename in (
                "pants_mask.png",
                "foreground.png",
                "overlay.png",
                "config.json",
                "metrics.json",
                "manifest.json",
            ):
                self.assertTrue((output_path / filename).is_file(), filename)
            manifest = json.loads((output_path / "manifest.json").read_text("utf-8"))
            self.assertEqual(manifest["protocol"]["path"], str(protocol_path.resolve()))
            self.assertEqual(len(manifest["protocol"]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
