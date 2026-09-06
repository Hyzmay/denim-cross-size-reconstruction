# Cross-Size Reconstruction Pipeline

Use this reference for architecture, implementation order, algorithm selection,
and debugging.

## Operating Principle

Preserve reliable source correspondences, deform according to target structure,
and complete only target pixels that lack a valid source sample. Minimize the
number of resampling operations because repeated warps destroy denim texture and
fine stitches.

## Stage Order

### 0. Input Standardization

Validate the input contract, orientation, view, source size, item profile,
resolution, background, and assumptions. Save the untouched source and hash.

### 1. Segmentation And Source Matting

Produce a hard garment mask, a soft source alpha, decontaminated foreground
colors, a trimap, and confidence. Estimate alpha before deformation. A final
edge smoother cannot recover a wrong source silhouette or white-fringe colors.

For segmentation ground truth report IoU, Dice, boundary IoU, and boundary F1.
Without ground truth report diagnostics as proxies only.

### 2. Layer And Accessory Separation

Separate denim body, structural details, decorative details, and removable
accessories. Do not warp hang tags as if they were denim. Keep permanent metal
hardware attached to its structural anchor.

### 3. Landmarks And Structure Curves

Estimate waistband, hip, crotch, knee, hem, outer seam, inseam, pocket boundary,
fly, belt loops, and relevant decorative anchors. Represent both confidence and
provenance. Keypoints alone are insufficient; curves and semantic regions define
the deformation constraints between them.

### 4. Canonical Pants Space

Build explicit source-image-to-canonical correspondence and its inverse or
validity map. The canonical representation should normalize garment structure,
not merely color a diagnostic UV image. Keep left/right legs, front/back view,
waistband, torso, upper/lower leg, and structural anchors distinguishable.

### 5. Size-Conditioned Target Geometry

Convert item-specific measurements into target landmarks, cross-sections, curves,
and silhouette constraints. Use paired size images or DXF during research when
available. Record estimated constraints and uncertainty instead of inventing
missing knee, rise, thigh, or hem values.

Geometry must be evaluated before rendering or completion.

### 6. Structure-Aware Deformation

Compare at least a simple similarity/affine baseline. Global TPS may be included
as a baseline, but it is not the preferred final method for a structured garment.
Use local TPS, piecewise-affine, constrained triangulation, ARAP-style, or another
justified field when non-rigid residuals require it.

Include garment boundary and internal structures as constraints. Check triangle
orientation, minimum area, foldovers, aspect ratio, local scale, angle/shear,
landmark error, and seam continuity before accepting the warp.

Warp foreground color, alpha, masks, coordinates, detail layers, and a source
validity map with the same transform. Prefer one final image resampling pass.

### 7. Detail Preservation

Use constraint types rather than a universal priority list:

- positional/topological constraints for seams, waistband, pockets and fly;
- low-distortion or rigid local transforms for logos and prints when justified;
- orientation/frequency constraints for twill and wash texture;
- separate compositing for removable accessories.

When using a learned or optimization model, detail losses may be introduced for
declared protected regions. Do not add a training loss to a classical baseline
that has no optimization objective.

### 8. Validity And New-Region Detection

Define:

```text
new_region = target_geometry AND NOT warped_source_validity
```

Also detect over-stretched samples, occlusions, holes, and seam breaks. The new
region is a correspondence result, not simply the band outside the old width.

### 9. Real Denim Texture Completion

Preserve valid mapped pixels. For repair regions, prefer same-image or verified
same-product donor patches with orientation, scale, color, wash-gradient, seam,
and boundary constraints. Use classical exemplar/PatchMatch, graph-cut seams,
frequency blending, or small-gap inpainting as supported by the evidence.

Save donor provenance and repetition diagnostics. Completion is repair, not a
replacement for correct target geometry.

### 10. Alpha-Aware Final Composite

Use the warped source alpha as the primary boundary observation, reconcile it
with target geometry, extend uncontaminated foreground colors, and composite once
onto the requested background. Inspect white/black halos, jaggies, shrinkage,
holes, and boundary color drift.

### 11. Validation And Reporting

Apply the gates in [evaluation.md](evaluation.md). Keep proxy quality separate
from physical geometry. Save the earliest failing stage and the next smallest
experiment.

## Recommended Development Order

1. Controlled single product and source-equals-target identity.
2. Segmentation, source alpha, accessory handling, and boundary ground truth.
3. Canonical coordinates and verified landmarks/curves.
4. One small size delta with DXF or paired target-size evidence.
5. Structure-aware mesh/TPS with validity diagnostics.
6. Detail constraints and real-texture repair.
7. Larger size deltas, multiple products, views, and failure cases.

Do not begin with human-worn garments, severe occlusion, or unrestricted product
photography unless the experiment is explicitly testing those failure cases.
