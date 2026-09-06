# Denim Cross-Size Reconstruction Research

Current release: `v0.3.0-p1-geometry-contract` (research prototype)

The repository now includes a first end-to-end, non-generative cross-size
baseline. It accepts a jeans product image plus source/target size, segments the
garment, infers structural levels, applies a region-aware row deformation, and
exports the reconstructed image and geometry diagnostics.

The reconstruction now estimates a source foreground alpha matte before
deformation, warps foreground color and alpha together, and records an identity
gate when source and target sizes match. The reported acceptance fields remain
image-quality proxies; they do not represent physical size validation without
DXF or same-item target-size ground truth.

See `CHANGELOG.md` for the v0.2 change list and verification status. This
release improves the P0 boundary/identity path; the target geometry is still a
row-wise proportional baseline and is not yet a validated industrial grading
system.

The current run contract also records the observed view, keeps output in the
same view, writes `target_geometry.json`, and separates proxy acceptance from
physical geometry status. `physical_geometry_status` remains
`not_evaluated` until DXF, paired target images, or verified measurements are
provided.

## Learning guides

- `docs/learning/01_项目完整理解_教师提问版.md`: current system, module data flow,
  artifacts, metrics, limitations, and oral-review questions in teaching order.
- `docs/learning/02_四篇论文与项目迁移_教师提问版.md`: GP-VTON, GaPT-DAR,
  ViTon-GUN, and DualFit, with original tasks separated from transferable ideas
  and the code's actual implementation status.
- `docs/learning/03_合并版Skill与项目执行框架.md`: merged v2 research skill,
  corrected phase gates, input contract, evaluation states, and paper transfer.

## Cross-size reconstruction

The included measurement profile is the item-specific chart published for
Taobao item `612962220220`. It is not presented as a universal Taobao standard.

```powershell
.\.venv\Scripts\python.exe -m denim_resize data\raw\phase0\sample_001\source.jpg `
  --output runs\sample_001-taobao-32-to-38 `
  --source-size 32 `
  --target-size 38
```

The run writes the reconstructed garment, stretched-source baseline,
side-by-side comparisons, inferred structure, target/new-region masks,
displacement field, scale map, texture donor diagnostics, metrics,
configuration, and provenance manifest. Newly exposed regions use a
deterministic classical exemplar-patch vote: low-frequency appearance follows
the geometry warp while high-frequency denim detail is transferred from valid
interior garment patches. Disable it for baseline comparisons with
`--texture-completion none`.

### Multi-size series

Generate several target sizes in one run while keeping every panel at the same
pixel scale:

```powershell
.\.venv\Scripts\python.exe -m denim_resize jeans.jpg `
  --output runs\jeans-multisize `
  --source-size 34 `
  --target-sizes 32,33,34,36,38
```

The root output includes `size_series.png`, `metrics.json`, `config.json`, and
`manifest.json`. Each `size_<size>/` directory contains the final image,
baseline and completion comparisons, canonical UV coordinates, ten semantic
regions, structure/detail masks, displacement and scale maps, new-region
diagnostics, and edge-refinement diagnostics.

The final edge stage extends garment colors outside the hard mask before
resampling, smooths only a tightly bounded contour region, and composites a
subpixel alpha edge. Its acceptance gate limits silhouette-area drift to 1.5%
and rejects increased contour roughness. Texture completion is also gated: a
candidate is retained only when coverage is at least 95% and the measured
texture-gradient gap does not increase. A rejected candidate falls back to the
geometry-warp baseline rather than forcing a visible texture artifact.

The checked-in Phase 0 results use the ratios from Taobao item
`612962220220` and assume source size 34 for the four visual samples. Those
ratios are an experiment profile, not verified measurements for the GUGR
products and not a universal Taobao size chart.

Regenerate the four-row, five-size overview with:

```powershell
.\.venv\Scripts\python.exe scripts\make_multisize_summary.py
```

See `docs/phase0/phase0_phase1_acceptance.md` for the current acceptance report
and unresolved data requirements.

## Segmentation-only command

```powershell
.\.venv\Scripts\python.exe -m denim_resize jeans.jpg --output runs\phase0-jeans
```

Attach a pre-registered sample protocol to the run manifest with
`--protocol docs\phase0\samples\sample_001_front_back.md`.

Optionally evaluate against a manually checked binary ground-truth mask:

```powershell
.\.venv\Scripts\python.exe -m denim_resize jeans.jpg `
  --output runs\phase0-jeans `
  --ground-truth jeans_mask.png
```

Each run writes `pants_mask.png`, `foreground.png`, `overlay.png`,
`config.json`, `metrics.json`, and `manifest.json`. The baseline is intended
for isolated or product-style garment images. Human-worn garments and complex
backgrounds are expected failure cases until a pretrained semantic baseline is
selected and evaluated on real project samples.

Run the tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
