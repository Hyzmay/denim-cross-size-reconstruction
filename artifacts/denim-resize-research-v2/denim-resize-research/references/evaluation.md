# Evaluation And Experiment Gates

Use this reference for metrics, claims, baselines, ablations, and acceptance.

## Three Separate Statuses

Never collapse all evaluation into one Boolean. Report at least:

```text
proxy_checks_passed: true | false
geometry_evaluated: true | false
physical_geometry_status: passed | failed | not_evaluated
```

`proxy_checks_passed=true` means only that declared image/deformation diagnostics
passed. It does not prove the target garment has the correct physical size.

## Identity Gate

Before cross-size evaluation, run source size equal to target size. Compare the
reconstructed output against the admitted source foreground in the same frame.

Measure:

- hard-mask IoU and boundary F1;
- alpha MAE in the boundary band;
- interior pixel MAE and exact-preservation coverage;
- landmark and curve displacement;
- changed-pixel map, including protected details;
- extra interpolation or blur introduced by the pipeline.

Initial thresholds may be strict because the requested geometry is unchanged,
but record them in configuration rather than hiding constants in code.

## Geometry Evaluation

With DXF, paired target-size images, or verified measurements, report as relevant:

- landmark and curve error in pixels and physical units;
- silhouette IoU, Chamfer distance, and Hausdorff distance;
- waistband, hip, thigh, knee, rise, outseam, inseam, and hem error when known;
- seam/notch alignment, area error, and pattern topology;
- uncertainty and camera-normalization error.

Without geometry truth, set physical geometry to `not_evaluated`.

## Deformation Evaluation

Report foldover count, invalid-source ratio, valid-source coverage, minimum
triangle area/orientation, local area and angle distortion, extreme scale/shear,
landmark residuals, and seam continuity. Reject singular maps and unexplained
invalid regions before texture completion.

## Detail And Texture Evaluation

Measure protected-region change, structural-anchor drift, line/stitch width and
continuity, twill orientation, gradient/frequency consistency, color drift,
donor coverage, repeated-patch artifacts, completion-boundary discontinuity, and
preserved-source coverage.

Use SSIM, perceptual metrics, or OCR only when the regions are aligned and the
metric matches the content. A perceptual score is not evidence of physical size.

## Boundary Evaluation

With alpha or boundary ground truth, report boundary F1/IoU, alpha error, trimap
error, foreground-color error, and contour distance. Always inspect halo color,
jaggies, contour roughness, area drift, holes, and edge shrinkage.

A smoother contour is not necessarily a more accurate contour.

## Baselines And Ablations

Useful baselines include identity, global resize, affine, global TPS, local TPS
or constrained mesh, and the same warp without completion. Use global TPS as a
comparison, not as an assumed final solution.

Candidate ablations may remove canonicalization, measurement conditioning,
structure constraints, detail constraints, source alpha propagation, validity
detection, or real-texture completion. Call a component a contribution only
after the experiment supports that claim.

## Experiment Record

Predeclare the question, baseline, changed variable, expected result, dataset
split, ground truth, metric, threshold, and stopping rule. Retain config, seed,
versions, input hashes, source revision, intermediate artifacts, visualizations,
metrics, failure cases, conclusion, and next experiment.

Change one factor per small experiment. Expand only when geometry, deformation,
texture, boundary, and reproducibility evidence agree.

## Human Review

For research claims, include blinded review by a pattern maker or garment expert
when feasible. Ask separately about silhouette, grading plausibility, structural
placement, seam continuity, wash/texture consistency, artifacts, and overall
acceptability rather than requesting one undifferentiated score.
