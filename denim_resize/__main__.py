from __future__ import annotations

import argparse
import json
from pathlib import Path

from .run import run_reconstruction, run_segmentation, run_size_series
from .segmentation import SegmentationConfig, SegmentationError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Segment jeans or reconstruct them at a merchant-chart target size."
    )
    parser.add_argument("image", type=Path, help="Input jeans image")
    parser.add_argument(
        "--output", type=Path, required=True, help="Run-specific output directory"
    )
    parser.add_argument("--source-size", help="Merchant-chart source size, e.g. 32")
    targets = parser.add_mutually_exclusive_group()
    targets.add_argument("--target-size", help="Merchant-chart target size, e.g. 38")
    targets.add_argument(
        "--target-sizes",
        help="Comma-separated merchant-chart targets, e.g. 32,33,34,36,38",
    )
    parser.add_argument(
        "--size-profile",
        default="taobao_612962220220",
        help="Item-specific merchant measurement profile",
    )
    parser.add_argument(
        "--view",
        choices=("front", "back", "unspecified"),
        default="unspecified",
        help="Observed garment view; output remains the same view",
    )
    parser.add_argument(
        "--ground-truth", type=Path, help="Optional binary mask for evaluation"
    )
    parser.add_argument(
        "--protocol", type=Path, help="Optional pre-registered experiment protocol"
    )
    parser.add_argument(
        "--method",
        choices=("border", "border-grabcut"),
        default="border-grabcut",
        help="Automatic foreground baseline",
    )
    parser.add_argument("--grabcut-iterations", type=int, default=5)
    parser.add_argument(
        "--texture-completion",
        choices=("exemplar", "none"),
        default="exemplar",
        help="Classical real-patch texture completion for newly exposed regions",
    )
    parser.add_argument(
        "--max-components",
        type=int,
        default=2,
        help="Maximum number of similarly sized garment views to retain",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    config = SegmentationConfig(
        use_grabcut=args.method == "border-grabcut",
        grabcut_iterations=args.grabcut_iterations,
        max_major_components=args.max_components,
    )
    try:
        has_targets = bool(args.target_size or args.target_sizes)
        if bool(args.source_size) != has_targets:
            raise ValueError(
                "--source-size requires either --target-size or --target-sizes"
            )
        if args.target_sizes:
            target_sizes = [
                value.strip() for value in args.target_sizes.split(",") if value.strip()
            ]
            result = run_size_series(
                args.image,
                args.output,
                source_size=args.source_size,
                target_sizes=target_sizes,
                size_profile_id=args.size_profile,
                view=args.view,
                segmentation_config=config,
                texture_completion=args.texture_completion,
            )
        elif args.source_size:
            result = run_reconstruction(
                args.image,
                args.output,
                source_size=args.source_size,
                target_size=args.target_size,
                size_profile_id=args.size_profile,
                view=args.view,
                segmentation_config=config,
                texture_completion=args.texture_completion,
            )
        else:
            result = run_segmentation(
                args.image,
                args.output,
                config=config,
                ground_truth_path=args.ground_truth,
                protocol_path=args.protocol,
            )
    except (FileNotFoundError, ValueError, SegmentationError) as error:
        raise SystemExit(f"run failed: {error}") from error
    print(
        json.dumps(
            {
                "output_directory": str(result.output_directory),
                "metrics": result.metrics,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
