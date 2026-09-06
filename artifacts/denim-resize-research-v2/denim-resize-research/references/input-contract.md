# Input Contract And Research Data

Use this reference before admitting a sample, mapping measurements to pixels,
handling accessories, or reading DXF.

## Deployment Contract

The intended user-facing inputs are:

- one isolated or near-isolated denim garment image;
- the real source size;
- a target size selected from an item-specific measurement profile.

The intended output is a target-size product image plus an evaluation record.
The user must not need to provide DXF.

This is not an unconstrained inverse-graphics claim. A single RGB image cannot
uniquely recover physical dimensions, hidden surfaces, camera geometry, or a
manufacturer's grading rules without additional evidence.

## First-Phase Admission Rules

Prefer images that satisfy all of the following:

- front or back view, approximately flat and upright;
- full garment visible with limited perspective distortion;
- separable background and adequate resolution;
- known source size and item-specific size chart;
- no severe folding, body pose, occlusion, or cropping.

Record complex backgrounds, human-worn garments, severe occlusion, and unknown
source sizes as failure cases until the corresponding method is implemented.

## Measurement Rules

- Preserve the merchant's measurement names, units, tolerances, and provenance.
- Do not treat one merchant profile as a universal sizing standard.
- Distinguish circumference from flat width; do not silently multiply or divide
  by two.
- Map each measurement to an explicit landmark, curve, cross-section, or derived
  constraint. A label alone is not a geometric correspondence.
- When thigh, knee, rise, hem, or another needed measurement is absent, use one
  of: `missing`, `estimated` with method and uncertainty, or `not_evaluated`.
- Keep source and target profiles item-specific and externally configurable.

Recommended metadata fields include product id, view, source/target size, chart
source, measurements, image path/hash, DXF or paired-image path when available,
annotation version, camera assumptions, and measurement confidence.

## Coordinate Frames

Name and document at least:

- source image pixels;
- source crop/component pixels;
- canonical garment coordinates;
- target geometry coordinates;
- output image pixels;
- DXF/model coordinates and physical units when DXF is present.

Represent conversions as named transforms or functions. Verify round trips on
landmarks and report residuals rather than relying on visual alignment.

## Garment And Accessory Layers

Do not use a single universal priority order. Assign constraints by role:

- **Denim body:** deformable appearance carrier.
- **Structural details:** waistband, seams, pockets, fly, belt loops, permanent
  buttons and rivets; preserve topology and structural anchors.
- **Decorative details:** prints, logos, embroidery, distressing and wash marks;
  preserve local appearance while respecting their garment anchors.
- **Removable accessories:** hang tags, hangers, clips, strings and unrelated
  product graphics; remove, mask, or composite separately.

Classify ambiguous metal parts by attachment and function. A permanent jeans
button is structural; a display clip is removable.

## DXF Research Contract

DXF alone is not enough. Confirm piece identity and source/target correspondence,
grain direction, seam and cut edges, notches, reference points, units, layers,
and whether seam allowance is included.

Parse relevant `LINE`, `LWPOLYLINE`, `POLYLINE`, `ARC`, `CIRCLE`, `SPLINE`, and
block references as required. Preserve the original entities and create a
separate sampled representation. Validate closure, winding, self-intersection,
duplicates, plausible dimensions, and topology before using geometry as truth.

## Required Failure States

Use explicit statuses such as:

- `input_rejected`: the first-phase image contract is not met;
- `measurement_missing`: required target constraints are absent;
- `geometry_not_evaluated`: no physical or paired ground truth exists;
- `correspondence_invalid`: landmarks, curves, or units are inconsistent;
- `deformation_invalid`: foldover, singularity, or invalid sampling occurred.

Do not replace one of these states with a successful image-quality proxy.
