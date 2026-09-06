from __future__ import annotations

import json
import platform
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import scipy

from .canonical import (
    build_canonical_garment,
    canonical_uv_visualization,
    semantic_region_visualization,
)
from .completion import (
    TextureCompletionConfig,
    complete_texture_exemplar,
    completion_region_visualization,
)
from .details import detect_detail_constraints, detail_visualization
from .edge import EdgeRefinementConfig, refine_garment_edge
from .io import read_bgr, read_binary_mask, sha256_file, write_image
from .deformation import (
    DeformationRatios,
    compose_component_alpha,
    compose_components,
    displacement_visualization,
    scale_visualization,
    warp_component,
)
from .matting import MattingConfig, estimate_foreground_matte
from .metrics import boundary_f1, mask_diagnostics, mask_dice, mask_iou
from .segmentation import SegmentationConfig, segment_pants
from .sizes import get_size_profile
from .structure import draw_structures, infer_pants_structures
from .visualization import (
    extract_foreground,
    make_comparison,
    make_overlay,
    make_size_series,
)


@dataclass(frozen=True, slots=True)
class RunResult:
    output_directory: Path
    metrics: dict[str, object]


def _git_revision() -> str | None:
    try:
        process = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return process.stdout.strip() if process.returncode == 0 else None


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run_segmentation(
    image_path: str | Path,
    output_directory: str | Path,
    config: SegmentationConfig | None = None,
    ground_truth_path: str | Path | None = None,
    protocol_path: str | Path | None = None,
) -> RunResult:
    source_path = Path(image_path).resolve()
    output_path = Path(output_directory).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    config = config or SegmentationConfig()

    image = read_bgr(source_path)
    result = segment_pants(image, config)
    mask = result.mask

    write_image(output_path / "pants_mask.png", mask.astype(np.uint8) * 255)
    write_image(output_path / "foreground.png", extract_foreground(image, mask))
    write_image(output_path / "overlay.png", make_overlay(image, mask))

    metrics: dict[str, object] = {
        **result.diagnostics,
        **mask_diagnostics(mask),
    }
    if ground_truth_path is not None:
        target = read_binary_mask(ground_truth_path, image.shape[:2])
        metrics.update(
            {
                "ground_truth_path": str(Path(ground_truth_path).resolve()),
                "iou": mask_iou(mask, target),
                "dice": mask_dice(mask, target),
                "boundary_f1_tolerance_2px": boundary_f1(mask, target, 2.0),
            }
        )

    protocol: dict[str, str] | None = None
    if protocol_path is not None:
        resolved_protocol = Path(protocol_path).resolve()
        if not resolved_protocol.is_file():
            raise FileNotFoundError(f"Protocol does not exist: {resolved_protocol}")
        protocol = {
            "path": str(resolved_protocol),
            "sha256": sha256_file(resolved_protocol),
        }

    manifest: dict[str, object] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_image": str(source_path),
        "source_sha256": sha256_file(source_path),
        "source_shape_hwc": list(image.shape),
        "source_color_space": "BGR uint8 (OpenCV)",
        "random_seed": config.random_seed,
        "protocol": protocol,
        "git_revision": _git_revision(),
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "opencv": cv2.__version__,
        },
    }
    _write_json(output_path / "config.json", config.to_dict())
    _write_json(output_path / "metrics.json", metrics)
    _write_json(output_path / "manifest.json", manifest)
    return RunResult(output_directory=output_path, metrics=metrics)


def run_reconstruction(
    image_path: str | Path,
    output_directory: str | Path,
    source_size: str,
    target_size: str,
    size_profile_id: str = "taobao_612962220220",
    segmentation_config: SegmentationConfig | None = None,
    texture_completion: str = "exemplar",
    completion_config: TextureCompletionConfig | None = None,
    edge_config: EdgeRefinementConfig | None = None,
    matting_config: MattingConfig | None = None,
) -> RunResult:
    source_path = Path(image_path).resolve()
    output_path = Path(output_directory).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    segmentation_config = segmentation_config or SegmentationConfig()
    completion_config = completion_config or TextureCompletionConfig()
    edge_config = edge_config or EdgeRefinementConfig()
    matting_config = matting_config or MattingConfig()
    if texture_completion not in {"exemplar", "none"}:
        raise ValueError("texture_completion must be 'exemplar' or 'none'")

    image = read_bgr(source_path)
    segmentation = segment_pants(image, segmentation_config)
    matte = estimate_foreground_matte(image, segmentation.mask, matting_config)
    structures = infer_pants_structures(segmentation.mask)
    if not structures:
        raise ValueError("No pants structures were inferred from the segmentation mask")
    canonical = build_canonical_garment(segmentation.mask, structures)

    profile = get_size_profile(size_profile_id)
    source_measurements, target_measurements = profile.pair(source_size, target_size)
    ratios = DeformationRatios.from_measurements(
        source_measurements, target_measurements
    )
    if min(ratios.waist, ratios.hip, ratios.knee, ratios.length) <= 0:
        raise ValueError("All deformation ratios must be positive")

    warped_components = [
        warp_component(
            matte.foreground_bgr,
            segmentation.mask,
            structure,
            ratios,
            source_alpha=matte.alpha,
        )
        for structure in structures
    ]
    reconstructed_baseline, target_mask, new_region, displacement, local_scale = (
        compose_components(warped_components)
    )
    target_alpha = compose_component_alpha(warped_components)
    details = detect_detail_constraints(reconstructed_baseline, target_mask)
    if texture_completion == "exemplar":
        completion = complete_texture_exemplar(
            reconstructed_baseline,
            target_mask,
            new_region,
            completion_config,
            protected_mask=details.protected_mask,
        )
        texture_completed = completion.image
    else:
        completion = None
        texture_completed = reconstructed_baseline
    edge_refinement = refine_garment_edge(
        texture_completed,
        target_mask,
        config=edge_config,
        alpha_hint=target_alpha,
    )
    reconstructed = edge_refinement.image

    unit_ratios = DeformationRatios(waist=1.0, hip=1.0, knee=1.0, length=1.0, front_rise=1.0)
    source_components = [
        warp_component(
            matte.foreground_bgr,
            segmentation.mask,
            structure,
            unit_ratios,
            source_alpha=matte.alpha,
        )
        for structure in structures
    ]
    source_foreground_hard, source_composed_mask, _, _, _ = compose_components(
        source_components
    )
    source_alpha = compose_component_alpha(source_components)
    source_edge_refinement = refine_garment_edge(
        source_foreground_hard,
        source_composed_mask,
        config=edge_config,
        alpha_hint=source_alpha,
    )
    source_foreground = source_edge_refinement.image

    if source_size == target_size:
        common_interior = cv2.erode(
            target_mask.astype(np.uint8), np.ones((5, 5), dtype=np.uint8)
        ).astype(bool)
        interior_mae = (
            float(
                np.mean(
                    np.abs(
                        reconstructed[common_interior].astype(np.float32)
                        - source_foreground[common_interior].astype(np.float32)
                    )
                )
            )
            if np.any(common_interior)
            else 0.0
        )
        identity_iou = mask_iou(edge_refinement.mask, source_composed_mask)
        identity_boundary_f1 = boundary_f1(
            edge_refinement.mask, source_composed_mask, 1.0
        )
        identity_alpha_mae = float(
            np.mean(
                np.abs(edge_refinement.alpha - source_edge_refinement.alpha)
            )
        )
        identity_metrics: dict[str, object] = {
            "applicable": True,
            "mask_iou": identity_iou,
            "boundary_f1_tolerance_1px": identity_boundary_f1,
            "interior_pixel_mae": interior_mae,
            "alpha_mae": identity_alpha_mae,
            "acceptance_passed": (
                identity_iou >= 0.999
                and identity_boundary_f1 >= 0.999
                and interior_mae <= 0.5
                and identity_alpha_mae <= 0.01
            ),
        }
    else:
        identity_metrics = {
            "applicable": False,
            "reason": "source and target sizes differ",
        }
    structure_view = draw_structures(make_overlay(image, segmentation.mask), structures)
    comparison = make_comparison(
        source_foreground,
        reconstructed,
        left_label=f"SOURCE (ASSUMED {source_size})",
        right_label=f"TARGET {target_size}",
    )
    new_region_view = reconstructed.copy()
    tint = np.zeros_like(new_region_view)
    tint[..., 2] = 255
    if np.any(new_region):
        new_region_view[new_region] = cv2.addWeighted(
            reconstructed[new_region], 0.45, tint[new_region], 0.55, 0
        )

    write_image(output_path / "source_mask.png", segmentation.mask.astype(np.uint8) * 255)
    write_image(
        output_path / "source_alpha.png",
        np.clip(matte.alpha * 255.0, 0, 255).astype(np.uint8),
    )
    source_matte_preview = (
        matte.foreground_bgr.astype(np.float32) * matte.alpha[..., None]
        + 255.0 * (1.0 - matte.alpha[..., None])
    )
    write_image(
        output_path / "source_foreground_matte.png",
        np.clip(source_matte_preview, 0, 255).astype(np.uint8),
    )
    write_image(output_path / "structure_landmarks.png", structure_view)
    write_image(
        output_path / "canonical_uv.png", canonical_uv_visualization(canonical)
    )
    write_image(
        output_path / "semantic_regions.png",
        semantic_region_visualization(canonical),
    )
    np.savez_compressed(
        output_path / "canonical_representation.npz",
        uv=canonical.uv,
        regions=canonical.regions,
    )
    write_image(output_path / "reconstructed_baseline.png", reconstructed_baseline)
    write_image(output_path / "reconstructed_texture_completed.png", texture_completed)
    write_image(output_path / "reconstructed.png", reconstructed)
    write_image(output_path / "comparison.png", comparison)
    write_image(output_path / "target_mask.png", target_mask.astype(np.uint8) * 255)
    write_image(
        output_path / "refined_target_mask.png",
        edge_refinement.mask.astype(np.uint8) * 255,
    )
    write_image(
        output_path / "edge_alpha.png",
        np.clip(edge_refinement.alpha * 255.0, 0, 255).astype(np.uint8),
    )
    write_image(output_path / "new_region_mask.png", new_region.astype(np.uint8) * 255)
    write_image(output_path / "new_region_overlay.png", new_region_view)
    write_image(output_path / "detail_protection_mask.png", details.protected_mask.astype(np.uint8) * 255)
    write_image(
        output_path / "detail_constraints.png",
        detail_visualization(reconstructed_baseline, details),
    )
    write_image(
        output_path / "edge_refinement_comparison.png",
        make_comparison(
            texture_completed,
            reconstructed,
            left_label="HARD MASK EDGE",
            right_label="REFINED EDGE",
        ),
    )
    if completion is not None:
        write_image(
            output_path / "texture_completion_regions.png",
            completion_region_visualization(
                reconstructed_baseline,
                new_region,
                completion.donor_candidate_mask,
                completion.donor_used_mask,
            ),
        )
        write_image(
            output_path / "texture_completion_comparison.png",
            make_comparison(
                reconstructed_baseline,
                texture_completed,
                left_label="STRETCHED BASELINE",
                right_label="EXEMPLAR COMPLETION",
            ),
        )
    write_image(
        output_path / "displacement_field.png",
        displacement_visualization(displacement, target_mask),
    )
    write_image(
        output_path / "local_scale_map.png",
        scale_visualization(local_scale, target_mask),
    )

    metrics: dict[str, object] = {
        **segmentation.diagnostics,
        "source_size": source_size,
        "target_size": target_size,
        "measurement_ratios": ratios.to_dict(),
        "component_count": len(structures),
        "components": [component.metrics for component in warped_components],
        "target_mask_area_px": int(np.count_nonzero(target_mask)),
        "new_region_area_px": int(np.count_nonzero(new_region)),
        "new_region_fraction_of_target": float(
            np.count_nonzero(new_region) / max(np.count_nonzero(target_mask), 1)
        ),
        "texture_completion": (
            completion.metrics
            if completion is not None
            else {"method": "stretched_source_baseline"}
        ),
        "detail_constraints": details.metrics,
        "source_matting": matte.metrics,
        "canonical_representation": canonical.metrics,
        "edge_refinement": edge_refinement.metrics,
        "identity_preservation": identity_metrics,
        "physical_geometry_evaluated": False,
        "evaluation_scope": "image-quality proxies; no DXF or target-size ground truth",
    }
    config_payload: dict[str, object] = {
        "source_size": source_size,
        "target_size": target_size,
        "size_profile": {
            "id": profile.profile_id,
            "merchant": profile.merchant,
            "item_id": profile.item_id,
            "source_url": profile.source_url,
            "retrieved_on": profile.retrieved_on,
            "units": profile.units,
        },
        "source_measurements": source_measurements.to_dict(),
        "target_measurements": target_measurements.to_dict(),
        "measurement_ratios": ratios.to_dict(),
        "segmentation": segmentation_config.to_dict(),
        "texture_completion": {
            "method": texture_completion,
            "config": completion_config.to_dict(),
        },
        "edge_refinement": edge_config.to_dict(),
        "matting": matting_config.to_dict(),
        "structure": [structure.to_dict() for structure in structures],
    }
    manifest: dict[str, object] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_image": str(source_path),
        "source_sha256": sha256_file(source_path),
        "source_shape_hwc": list(image.shape),
        "git_revision": _git_revision(),
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "opencv": cv2.__version__,
        },
    }
    _write_json(output_path / "config.json", config_payload)
    _write_json(output_path / "metrics.json", metrics)
    _write_json(output_path / "manifest.json", manifest)
    return RunResult(output_directory=output_path, metrics=metrics)


def run_size_series(
    image_path: str | Path,
    output_directory: str | Path,
    source_size: str,
    target_sizes: list[str],
    size_profile_id: str = "taobao_612962220220",
    segmentation_config: SegmentationConfig | None = None,
    texture_completion: str = "exemplar",
    completion_config: TextureCompletionConfig | None = None,
    edge_config: EdgeRefinementConfig | None = None,
    matting_config: MattingConfig | None = None,
) -> RunResult:
    if not target_sizes:
        raise ValueError("At least one target size is required")
    matting_config = matting_config or MattingConfig()
    ordered_sizes = list(dict.fromkeys(target_sizes))
    profile = get_size_profile(size_profile_id)
    profile.pair(source_size, source_size)
    for target_size in ordered_sizes:
        profile.pair(source_size, target_size)

    output_path = Path(output_directory).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    size_results: dict[str, dict[str, object]] = {}
    series_images: list[np.ndarray] = []
    series_labels: list[str] = []
    for target_size in ordered_sizes:
        result = run_reconstruction(
            image_path,
            output_path / f"size_{target_size}",
            source_size=source_size,
            target_size=target_size,
            size_profile_id=size_profile_id,
            segmentation_config=segmentation_config,
            texture_completion=texture_completion,
            completion_config=completion_config,
            edge_config=edge_config,
            matting_config=matting_config,
        )
        size_results[target_size] = result.metrics
        series_images.append(read_bgr(result.output_directory / "reconstructed.png"))
        suffix = " (SOURCE)" if target_size == source_size else ""
        series_labels.append(f"SIZE {target_size}{suffix}")

    write_image(
        output_path / "size_series.png",
        make_size_series(series_images, series_labels),
    )
    acceptance = {
        size: bool(
            metrics["source_matting"]["acceptance_passed"]
            and metrics["texture_completion"].get("acceptance_passed", True)
            and metrics["edge_refinement"]["acceptance_passed"]
            and metrics["identity_preservation"].get("acceptance_passed", True)
        )
        for size, metrics in size_results.items()
    }
    metrics: dict[str, object] = {
        "source_size": source_size,
        "target_sizes": ordered_sizes,
        "per_size_acceptance": acceptance,
        "all_sizes_accepted": all(acceptance.values()),
        "all_proxy_checks_passed": all(acceptance.values()),
        "physical_geometry_evaluated": False,
        "runs": size_results,
    }
    config: dict[str, object] = {
        "source_size": source_size,
        "target_sizes": ordered_sizes,
        "size_profile_id": size_profile_id,
        "texture_completion": texture_completion,
        "matting": matting_config.to_dict(),
    }
    source_path = Path(image_path).resolve()
    manifest: dict[str, object] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_image": str(source_path),
        "source_sha256": sha256_file(source_path),
        "git_revision": _git_revision(),
    }
    _write_json(output_path / "config.json", config)
    _write_json(output_path / "metrics.json", metrics)
    _write_json(output_path / "manifest.json", manifest)
    return RunResult(output_directory=output_path, metrics=metrics)
