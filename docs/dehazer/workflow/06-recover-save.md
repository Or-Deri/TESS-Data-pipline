# 06 — Recover & Save (Step 4)

## Goal

Invert the haze model with smoothed $A$ and smoothed $t$, denormalize to the
original physical scale, and write `dehazed__*.fits` plus the output-location
marker.

## Inputs / outputs

| Kind | Detail |
|---|---|
| Input | Normalized `cube[i]`; smoothed $A_i$; smoothed `t_cube[i]`; metadata `orig_min`, `orig_max`, `filename` |
| Output | `dehazed__<original_filename>.fits` — single `PrimaryHDU`, `float64`, HDU 0 |
| Output | `OUTPUT_LOCATION.txt` in `output_dir` after the full run |

## Constants

| Field | Default / value |
|---|---|
| `t_min_clip` | `0.01` |
| Output filename prefix | `dehazed__` |
| Output HDU | Primary HDU (index 0) |
| Skip-if-exists | If target path exists, skip that frame |

## Algorithm

### Scene recovery (`recover_image`)

[tess_dehazing/core/recovery.py](../../../paloma/cleaning/dehazer/core/recovery.py); thesis Eq. 3.12. For
each frame, using **smoothed** $A_i$ and **smoothed** $t_i$:

1. `t_safe = maximum(t_map, t_min_clip)` (`0.01`).
2. `recovered = (image - A_i) / t_safe + A_i`.
3. `recovered = clip(recovered, 0.0, 1.0)`.

### Denormalize & save

1. Move to CPU (`to_cpu`) if on GPU.
2. `result = recovered * (orig_max - orig_min) + orig_min` — using the
   **global** min/max stored in metadata ([02-load-normalize](02-load-normalize.md)).
3. Save via `save_fits` ([io/fits_io.py](../../../paloma/cleaning/dehazer/io/fits_io.py)): wrap in a single
   `fits.PrimaryHDU(result)`, write with `overwrite=True`. The output array is
   `float64`, stored in **HDU 0** (the primary HDU). Parent dirs are created.
4. Filename: `dehazed__` + original basename.

### Output Contract

| Aspect | Specification |
|---|---|
| Filename | `dehazed__<original_filename>.fits` |
| FITS structure | Single `PrimaryHDU`, data in HDU 0, `float64` |
| Pixel scale | Original physical counts (denormalized via global min/max) |
| Skip-if-exists | If the target path already exists, that frame is **skipped** (not recomputed/overwritten) |
| Location marker | `OUTPUT_LOCATION.txt` written in `output_dir` after the run, listing absolute output/input paths, a pipeline label, and the count of `dehazed__*.fits` |

### Structured (notebook-style) layout

`structured_dehaze_output_dir` ([io/layout.py](../../../paloma/cleaning/dehazer/io/layout.py)):

```
{output_base}/output_{sector}_GlobalNorm_Subfolders/{slug}/
```

The parameter **slug** (`params_folder_name`) is
`ps{patch_size}_vt{vt}_nnd{nnd}`. Formatting rules:

- `vt` (`variance_threshold`): `0` if zero; for `|vt| >= 1e-2` use `f"{vt:g}"`;
  for `1e-12 <= |vt| < 1e-2` use `f"{vt:.12f}"` with trailing zeros and dot
  stripped; else `f"{vt:.6g}"`. **Default `5e-5` → `0.00005`.**
- `nnd` (`nn_dist_threshold`): integer form if integral, else `f"{nnd:g}"`.
  **Default `0.3` → `0.3`.**
- With defaults the slug is **`ps9_vt0.00005_nnd0.3`**.

## Code anchors

- `recover_image` — [tess_dehazing/core/recovery.py](../../../paloma/cleaning/dehazer/core/recovery.py)
- `denormalize` — [tess_dehazing/io/normalize.py](../../../paloma/cleaning/dehazer/io/normalize.py); `save_fits` — [tess_dehazing/io/fits_io.py](../../../paloma/cleaning/dehazer/io/fits_io.py)
- `to_cpu` — [tess_dehazing/core/backend.py](../../../paloma/cleaning/dehazer/core/backend.py)
- `_write_output_location_marker` — [tess_dehazing/pipeline/orchestration.py](../../../paloma/cleaning/dehazer/pipeline/orchestration.py)
- `params_folder_name`, `structured_dehaze_output_dir` — [tess_dehazing/io/layout.py](../../../paloma/cleaning/dehazer/io/layout.py)

## Ordering constraints

- Recovery uses the **smoothed** $A$ and **smoothed** $t$ only.
- Skip-if-exists means a dirty output directory prevents a fresh reproduction —
  clean before acceptance runs ([07-ops](07-ops.md), [08-verification](08-verification.md)).

## Navigation

← [Prev: 05-transmission](05-transmission.md) · [Next: 07-ops](07-ops.md) →
