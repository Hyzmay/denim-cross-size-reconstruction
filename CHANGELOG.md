# Changelog

## v0.2.0-p0-boundary-alpha - 2026-09-07

This research release strengthens Phase 0 boundary handling and source-equals-
target validation while keeping the project non-generative.

### Added

- Source foreground alpha matting and boundary-color decontamination before
  deformation.
- Consistent foreground/alpha propagation through deformation and final edge
  compositing.
- Source-equals-target identity metrics for mask IoU, boundary F1, interior
  pixel MAE, and alpha MAE.
- Explicit proxy-evaluation scope in run metrics, including
  `physical_geometry_evaluated: false` when no DXF or paired target ground truth
  is available.
- Chinese learning guides and the merged v2 `denim-resize-research` skill
  package under `docs/learning/` and `artifacts/`.

### Verification

- Unit tests: 22 passing.
- Python compilation: `denim_resize` and `tests` compile successfully.
- The source-equals-target identity sample passes the declared gate.

### Known limits

- Target geometry remains a proportional row-wise deformation baseline.
- Acceptance fields are image-quality proxies, not proof of physical size
  accuracy.
- Production claims require same-item size measurements, DXF or paired target
  images, and manually verified masks/landmarks.
- The repository intentionally excludes local source images, `runs/`, raw data,
  and virtual environments.
