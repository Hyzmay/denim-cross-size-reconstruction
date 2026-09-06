"""Single-image denim cross-size reconstruction research tools."""

from .canonical import CanonicalGarment, build_canonical_garment
from .completion import TextureCompletionConfig, complete_texture_exemplar
from .edge import EdgeRefinementConfig, refine_garment_edge
from .evaluation import EvaluationStatus
from .geometry import TargetGeometry, build_target_geometry
from .segmentation import (
    SegmentationConfig,
    SegmentationError,
    SegmentationResult,
    segment_pants,
)
from .run import run_reconstruction, run_size_series

__all__ = [
    "TextureCompletionConfig",
    "complete_texture_exemplar",
    "CanonicalGarment",
    "build_canonical_garment",
    "EdgeRefinementConfig",
    "refine_garment_edge",
    "EvaluationStatus",
    "TargetGeometry",
    "build_target_geometry",
    "SegmentationConfig",
    "SegmentationError",
    "SegmentationResult",
    "segment_pants",
    "run_reconstruction",
    "run_size_series",
]
