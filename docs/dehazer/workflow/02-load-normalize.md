# 02 — Load & Normalize

## Goal

Discover, order, load, crop, and **globally** normalize a batch of TESS FITS
frames into a float64 cube in $[0,1]$ with shared denormalization bounds.

## Inputs / outputs

| Kind | Detail |
|---|---|
| Input | `input_dir` of `*.fits`; `DehazeConfig` (`num_frames`, `fits_extension`, `crop_bottom`, `crop_sides`) |
| Output | `data_cube` shape $(N, H, W)$, `float64`, values in $[0, 1]$ |
| Output | `metadata[i] = {orig_min, orig_max, filename}` — same `orig_min`/`orig_max` for every frame in the batch |

## Constants

| Field | Default |
|---|---:|
| `num_frames` | `10` |
| `fits_extension` | `1` |
| `crop_bottom` | `30` |
| `crop_sides` | `44` |

## Algorithm

### File discovery & ordering

Implemented in [tess_dehazing/io/fits_io.py](../../../paloma/cleaning/dehazer/io/fits_io.py).

- Files are found with `sorted(glob.glob(os.path.join(input_dir, "*.fits")))`.
- The list is truncated to the first `num_frames` (default 10) entries.
- Empty directory → `FileNotFoundError`.
- **Ordering is alphabetical by full path** and must be preserved — the temporal
  axis is defined by this order.

### Per-file loading (`load_single_fits`) — FITS load & crop

For each file, in order:

1. Open with `astropy.io.fits`; read `hdul[cfg.fits_extension].data`
   (**HDU index 1** by default — the TESS FFI science extension). `None` data → `ValueError`.
2. Cast to `np.float64`.
3. `np.nan_to_num(data)` — replace `NaN` with `0.0` (and `±inf` with large finite values, per NumPy defaults).
4. **Crop calibration edges** (`_crop_frame`): for an $H \times W$ frame,
   keep `data[0 : H - crop_bottom, crop_sides : W - crop_sides]`, i.e. trim the
   bottom `30` rows and `44` columns from each side. A native $2078 \times 2136$
   TESS FFI becomes $2048 \times 2048$.

Output per file: a 2-D `float64` array with NaNs zeroed and calibration edges
trimmed. Keep a record of the original basename for the output filename.

### Global normalization

Implemented in `load_fits_directory(...)`
([io/fits_io.py](../../../paloma/cleaning/dehazer/io/fits_io.py)).

1. Compute, across **all frames in the batch**:
   - `global_min = min over frames of np.min(frame)`
   - `global_max = max over frames of np.max(frame)`
2. If `global_max <= global_min` → `ValueError`.
3. For each frame: `normed = (frame - global_min) / (global_max - global_min)`.
   (`normalize()` returns zeros if range $\le 0$.)
4. **Every frame's metadata stores the same `orig_min = global_min` and
   `orig_max = global_max`.** This is what makes denormalization physically
   consistent across the sequence.

Output: `data_cube` shape $(N, H, W)$, `float64`, values in $[0, 1]$, plus
`metadata[i] = {orig_min, orig_max, filename}`.

> The batch **must** use a single global scale (not per-frame min/max), so the
> whole sequence is denormalized consistently.

### Sector inference (structured layout only)

`infer_sector_label` ([io/layout.py](../../../paloma/cleaning/dehazer/io/layout.py)):

- If the input directory basename matches `^s\d+-\d+-\d+$` (e.g. `s0003-1-1`),
  use it directly.
- Else parse the first sorted FITS filename for a `-s(\d+-\d+-\d+)-` segment and
  prefix with `s`.
- Else sanitize the basename (`[^\w.\-]+` → `_`), or `unknown_sector`.

## Code anchors

- `get_fits_files`, `load_single_fits`, `_crop_frame`, `load_fits_directory` — [tess_dehazing/io/fits_io.py](../../../paloma/cleaning/dehazer/io/fits_io.py)
- `normalize` — [tess_dehazing/io/normalize.py](../../../paloma/cleaning/dehazer/io/normalize.py)
- `infer_sector_label` — [tess_dehazing/io/layout.py](../../../paloma/cleaning/dehazer/io/layout.py)

## Ordering constraints

- Alphabetical sort defines the temporal axis; do not re-order after discovery.
- Global norm must use **all frames in the current batch** before any airlight
  estimation.
- Batching changes the global min/max scope — see [07-ops](07-ops.md#batching-semantics).

## Navigation

← [Prev: 01-setup](01-setup.md) · [Next: 03-estimate-airlight](03-estimate-airlight.md) →
