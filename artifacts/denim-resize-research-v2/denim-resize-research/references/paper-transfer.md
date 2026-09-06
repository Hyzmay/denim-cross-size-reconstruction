# Paper Reading And Method Transfer

Use this reference when researching GP-VTON, ViTon-GUN, GaPT-DAR, DualFit, or
when claiming that this project implements a paper method.

## Full-Paper Protocol

Read the complete main paper and available supplementary material. Cover abstract,
introduction, related work, method, architecture, equations, losses, datasets,
experiments, ablations, limitations, and implementation details. Track official
code and citations when available.

For every paper, report four separate statements:

1. the original problem, inputs, outputs, data, and assumptions;
2. the transferable principle for denim cross-size reconstruction;
3. the parts that do not transfer or require unavailable training data;
4. what the current code actually implements, with evidence.

Conceptual similarity is not a reproduction. Do not claim novelty merely because
several published components are combined.

## GP-VTON

**Original problem:** general-purpose image-based virtual try-on conditioned on
a person and garment, using collaborative local-flow and global-parsing learning.

**Transfer:** semantic regions should receive appropriate local deformation and
be assembled with global consistency. Its motivation against texture squeezing
is relevant to pockets, seams, waistband, legs, and decorative regions.

**Do not transfer blindly:** the person-conditioned parsing/generation task,
training losses, and learned local flow are not equivalent to a row-wise scale,
TPS baseline, or a single garment image. Call it GP-VTON-style only when the
implemented architecture and training evidence justify that wording.

## ViTon-GUN

**Original problem:** person-to-person virtual try-on decomposed through garment
unwrapping into a canonical A-pose garment and subsequent garment-to-person warp.

**Transfer:** separate appearance from target geometry through explicit
source-to-canonical and canonical-to-target correspondence. This is especially
useful for learning a stable canonical pants representation.

**Do not transfer blindly:** a diagnostic UV map is not learned unwrapping. The
project needs bidirectional correspondence, validity, structure alignment, and
evidence that canonicalization improves geometry or detail preservation.

## GaPT-DAR

**Original problem:** category-level garment pose tracking for robotic operation
using integrated 2D deformation and 3D reconstruction from garment point-cloud
observations and canonical representations.

**Transfer:** explicit, interpretable 2D deformation, canonical shape priors,
TPS-style registration, and geometry supervision are relevant. DXF can provide
research-time canonical geometry or correspondence evidence.

**Do not transfer blindly:** a single RGB product image does not provide the
paper's point clouds, NOCS state, temporal input, depth reconstruction, or 3D
tracking supervision. Use the 2D principle without claiming the 3D method.

## DualFit

**Original problem:** two-stage virtual try-on based on garment warping followed
by synthesis/repair.

**Transfer:** distinguish reliable warped source pixels from regions that truly
require repair, and give special attention to the interface between preserved
and repaired areas.

**Do not transfer blindly:** this project currently excludes generative garment
synthesis. Implement the transferable separation with explicit validity masks
and classical real-texture completion unless the project scope changes.

## Combined Research Hypothesis

A defensible project hypothesis is:

```text
canonical pants correspondence
-> measurement-conditioned explicit target geometry
-> semantic local deformation with global consistency
-> validity-aware preservation and classical real-texture repair
```

Treat this as a candidate research system. Establish novelty through a complete
related-work search, formal problem definition, matched baselines, ablations,
and geometry/detail/texture/boundary evidence.
