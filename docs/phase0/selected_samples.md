# Phase 0 selected jeans samples

Selection date: 2026-09-06

The public merchant images below are research inputs for segmentation and
geometry experiments. Product pages and measurements can change. Each source
file is preserved with its retrieval metadata; no page is treated as a
universal Taobao size standard.

## Primary isolated-garment set

Samples 002, 006, 007, and 008 are color/material variants from the same GUGR
straight-leg listing. Using a shared silhouette isolates foreground/texture
contrast as the changed variable before adding style variation.

- Item: `834843856254`
- Merchant: GUGR 線上購買平台
- Public URL: https://item.taobao.com/item.htm?id=834843856254
- Sizes shown: `28, 29, 30, 31, 32, 33, 34, 36, 38, 40`
- Limitation: the page exposed size choices but no centimetre measurement table
  during retrieval. These samples must not be used for merchant-accurate
  cross-size geometry until a verified chart is obtained.
- Acquisition: rendered public product images were captured through the
  connected browser and cropped only to remove browser background bars. The
  processed image dimensions and SHA-256 hashes are recorded in
  `data/raw/phase0/selected_samples/prepared_files.json`.

Source image URLs:

- `sample_002_gugr`: https://gw.alicdn.com/bao/uploaded/i1/2606501341/O1CN01vCtR9d1LmE79kHsry_!!2606501341.jpg_.webp
- `sample_006_gugr_black`: https://gw.alicdn.com/bao/uploaded/i1/2606501341/O1CN01UgmNkl1LmE791QVQM_!!2606501341.jpg_.webp
- `sample_007_gugr_raw_indigo`: https://gw.alicdn.com/bao/uploaded/i1/2606501341/O1CN01tnRi7D1LmE7BlfSq4_!!2606501341.jpg_.webp
- `sample_008_gugr_offwhite`: https://gw.alicdn.com/bao/uploaded/i3/2606501341/O1CN01lnbQrw1LmE9zpfZaD_!!2606501341.jpg_.webp

| Sample | Appearance | Role | Segmentation result |
|---|---|---|---|
| `sample_002_gugr` | washed grey-blue | main clean baseline | visual pass, 1 component |
| `sample_006_gugr_black` | washed black | dark-texture contrast | visual pass, 1 component |
| `sample_007_gugr_raw_indigo` | raw indigo | low-wash/detail baseline | visual pass, 1 component |
| `sample_008_gugr_offwhite` | off-white | low garment/background contrast | visual pass, 1 component |

The older `sample_001` remains useful because it contains aligned front and
back views and a different slim silhouette. It should be retained alongside
this new set rather than replaced.

## Failure and future-robustness set

These images are deliberately not accepted as current cross-size inputs. They
are retained to define the next segmentation/garment-parsing problems.

| Sample | Public item | Failure variable | Current baseline |
|---|---|---|---|
| `sample_003_wassup` | `824133962191` | wearer, sweatshirt, hands, drawstrings, promotional text | body and garment merge |
| `sample_004_sdk` | `978242073349` | wearer, dark complex scene, occlusion | no foreground survives |
| `sample_005_large_size` | `612962220220` | wearer, hands, belt, large text overlay | text selected instead of pants |

Merchant charts available for later size-conditioned experiments:

- Item `824133962191`: L/XL/2XL waist `76/80/84`, hip `112.5/116.5/120.5`,
  length `104.5/106.5/108.5` cm.
- Item `978242073349`: M/L/XL waist `70/74/78`, length `106/107/108` cm;
  hip/knee measurements were not exposed and must not be guessed.
- Item `612962220220`: the verified `32-38` chart is recorded separately in
  `docs/phase0/taobao_size_profile_612962220220.md`.

## Acceptance decision

The immediate Phase 0/1 working set is `sample_001`, `sample_002`,
`sample_006`, `sample_007`, and `sample_008`. Samples 003-005 are a held-out
failure set. The next shape-diversity expansion should add clean isolated slim,
tapered, and flared listings with item-specific centimetre charts.
