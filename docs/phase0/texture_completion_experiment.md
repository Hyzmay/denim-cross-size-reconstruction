# Phase 0 Classical Denim Texture Completion

## Question and gate

Can deterministic exemplar-patch texture transfer make the newly exposed area
of a `32 -> 38` geometry warp closer to the garment's valid interior texture
without changing preserved garment pixels or introducing an interface jump?

The pre-registered minimum gate for this iteration was:

- at least 95% of the detected new region receives a valid donor;
- the new-region gradient-energy gap to the donor region does not increase;
- pixels outside the new region remain unchanged.

The comparison baseline is the existing region-aware warp with cubic sampling.
The single changed factor is high-frequency residual transfer from valid
interior denim patches. No learned or generative model is used.

## Final clean-sample results

| Sample | Coverage | Gradient gap before | Gradient gap after | Strength | Interface MAE | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `sample_002_gugr` | 100% | 0.515 | 0.515 | 0.000 | 0.000 | pass, baseline already within tolerance |
| `sample_006_gugr_black` | 100% | 7.771 | 0.574 | 0.875 | 0.046 | pass |
| `sample_007_gugr_raw_indigo` | 100% | 5.904 | 3.512 | 1.000 | 0.023 | pass |
| `sample_008_gugr_offwhite` | 100% | 2.808 | 0.043 | 0.250 | 0.016 | pass |

Gradient values use grayscale Sobel magnitude. Interface MAE is measured on a
one-pixel new/preserved boundary and is reported on the 0-255 image scale.

## Method

The completion stage separates each warped garment into a smooth base and a
high-frequency residual. It builds local Lab color, texture-variance, gradient,
and normalized-position descriptors for valid donor patches. New-region patches
retrieve nearby compatible exemplars with a deterministic nearest-neighbor
index. A coherent inward mirror mapping is blended with overlapping patch votes
to avoid averaging away fine raw-denim grain. The transfer strength is selected
from a fixed search grid against donor gradient energy, while the first boundary
ring remains the geometry-warp baseline for continuity.

## Conclusion and limitations

The Phase 0 hypothesis passes on the four clean isolated samples under the
defined metric gate. The method preserves all pixels outside the detected new
region and is deterministic. This is evidence for local denim-grain repair, not
for production-ready semantic reconstruction: it does not yet understand seam
topology, extend pocket shapes, synthesize missing labels, or verify physical
dimensions for these GUGR samples. Their item page did not expose a centimetre
measurement table, so the `32 -> 38` geometry ratios are an explicitly labelled
visual experiment borrowed from verified Taobao item `612962220220`, not ground
truth for the GUGR product.
