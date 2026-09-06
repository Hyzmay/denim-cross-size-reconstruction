---
name: denim-resize-research
description: Develop and evaluate non-generative, single-image denim cross-size reconstruction pipelines using known source and target sizes, with DXF or paired images used only for research supervision and evaluation. Use for architecture, experiments, implementation, debugging, paper-method transfer, and evidence-backed validation; do not use for ordinary bitmap resizing or generative garment synthesis.
---

# Denim Resize Research

Build a reproducible computer-vision system for:

```text
single denim garment image + known source size + target size/profile
-> target-size garment image with controlled geometry and preserved real detail
```

The deployment interface must not require DXF. Use DXF, paired cross-size images,
measurements, and annotations only as research supervision or evaluation evidence.

## Read The Relevant Reference

- For sample admission, measurements, coordinate frames, accessories, or DXF
  semantics, read [references/input-contract.md](references/input-contract.md).
- For architecture, algorithms, implementation order, or debugging, read
  [references/cross-size-pipeline.md](references/cross-size-pipeline.md).
- For experiment design, metrics, gates, baselines, or result claims, read
  [references/evaluation.md](references/evaluation.md).
- For GP-VTON, ViTon-GUN, GaPT-DAR, DualFit, or literature transfer, read
  [references/paper-transfer.md](references/paper-transfer.md).

Read only the references needed for the current request.

## Non-Negotiable Invariants

- Preserve the source file and write every run to a separate output directory.
- Do not use diffusion, GAN, image-to-image, or other generative garment models.
  Prefer registration, constrained warping, and classical exemplar completion.
- Do not treat size change as ordinary bitmap scaling. Predict target structure,
  deform only where geometry requires it, and complete only pixels without a
  valid source correspondence.
- Do not invent missing garment measurements. Mark them as missing, estimate
  them explicitly with uncertainty, or stop the geometry claim.
- Separate denim body, structural details, decorative details, and removable
  accessories. Give each layer constraints appropriate to its semantics.
- Estimate source alpha and decontaminate boundary colors before deformation.
  Warp foreground, alpha, masks, coordinates, and validity maps consistently.
- Keep coordinate systems and transforms explicit. Test landmark round trips.
- Evaluate geometry before texture. Texture repair cannot compensate for a
  wrong silhouette, correspondence, foldover, or invalid mask.
- Without DXF, a paired target-size image, or another declared geometry ground
  truth, report geometry as `not_evaluated`; never turn proxy checks into a
  physical-accuracy claim.

## Research Workflow

1. State one falsifiable question, a baseline, one changed variable, and a
   predeclared success criterion.
2. Apply the input contract. Record known facts, missing facts, assumptions,
   units, camera conditions, and whether physical geometry can be evaluated.
3. Establish a source-equals-target identity run before cross-size experiments.
   It must preserve the interior, mask, boundary, alpha, and structural anchors.
4. Establish source mask, source alpha, accessory layers, landmarks, structure
   curves, canonical coordinates, and validity maps before texture completion.
5. Predict target geometry from item-specific measurements and available shape
   priors. Use DXF only when present in the research data.
6. Begin with the least flexible transform justified by correspondences. Move
   from similarity/affine baselines to local TPS, constrained mesh, or related
   non-rigid methods only when residual structure requires them.
7. Check deformation validity before rendering: foldovers, triangle areas,
   extreme scale/shear, invalid sampling, and seam or landmark residuals.
8. Preserve valid mapped source pixels. Detect new, occluded, or over-stretched
   regions explicitly, then repair only those regions with real source texture.
9. Save machine-readable artifacts and visual diagnostics for every stage.
10. Expand from identity to a small known size delta, then larger deltas,
    additional products, views, patterns, and failure cases.

## Engineering Contract

- Use Python and established scientific libraries already present in the
  project. Use OpenCV for image operations and `ezdxf` for DXF when required.
- Keep input handling, segmentation/matting, layer separation, structure,
  canonicalization, target geometry, deformation, completion, evaluation,
  visualization, and orchestration in separate modules with typed interfaces.
- Represent landmarks, curves, transforms, meshes, alpha, masks, and validity
  maps explicitly; avoid ambiguous bare arrays across module boundaries.
- Preserve DXF units, layers, entity types, open/closed status, and curve
  semantics. Record curve-flattening tolerance when sampling is necessary.
- Fail clearly on unknown units, missing required profile fields, empty masks,
  insufficient correspondences, singular transforms, mesh foldovers, or invalid
  source mappings. Do not silently guess.
- Record configuration, random seed, dependency versions, input hashes, source
  revision, assumptions, and the exact evaluation scope.
- Add focused tests for coordinates, alpha/mask propagation, DXF sampling,
  mesh validity, identity preservation, and one end-to-end experiment.

## Phase Gates

- **P0 Boundary and identity:** controlled product image, mask, source alpha,
  accessory handling, and source-equals-target identity gate.
- **P1 Geometry:** canonical representation, measurement-conditioned target
  landmarks/curves, DXF or paired-image evaluation, and a small size delta.
- **P2 Deformation and detail:** structure-aware local deformation, explicit
  validity, detail constraints, and foldover/distortion checks.
- **P3 Completion and scale-up:** new-region detection, classical real-texture
  completion, batch evaluation, ablations, additional products and views.

Do not advance a phase because the final image merely looks plausible. Advance
only when its declared gate passes or the remaining uncertainty is recorded.

## Required Run Outputs

At minimum retain:

- config, seed, versions, input identifiers/hashes, and source revision;
- source mask/alpha, layers, landmarks, curves, and canonical representation;
- target geometry, correspondences, mesh/field, validity and distortion maps;
- preserved/new/repair masks, donor provenance, and completion diagnostics;
- final alpha/composite, metrics, evaluation status, failure notes, and next
  smallest experiment.

The project may use a layout such as
`runs/<experiment-id>/{config,artifacts,figures,metrics,notes}` when no stronger
local convention exists.
