# 07 — Ops (GPU, Batching, Determinism)

## Goal

Enumerate optional GPU behavior, batching semantics, and every determinism /
reproducibility caveat that can change numeric output.

## Inputs / outputs

| Kind | Detail |
|---|---|
| Input | `DehazeConfig.use_gpu`, `batch_size`; installed OpenCV/CuPy backends |
| Effect | Whether ops run on CPU or GPU; whether global norm / temporal smooth span the full sequence |

## Constants

| Concern | Value |
|---|---|
| Free-VRAM threshold for GPU | ≥ 50 % free on device 0 |
| Compute-utilization reject | ≥ 50 % via `nvidia-smi` when available |
| Default `batch_size` | `None` (single batch = full sequence) |

## Algorithm

### GPU Acceleration (optional)

Opt-in via `--gpu`. `_resolve_gpu`
([pipeline/orchestration.py](../../../paloma/cleaning/dehazer/pipeline/orchestration.py)):

1. If `cfg.use_gpu` is false → return `False` (pure CPU; bit-for-bit legacy behavior).
2. `detect_gpu()` — `import cupy`, `cp.cuda.Device(0).use()`, allocate a tiny
   array; any exception → CPU.
3. `is_gpu_free()` — require **≥ 50 % free VRAM** on device 0; additionally, if
   `nvidia-smi` is available, reject when GPU **compute utilization ≥ 50 %**.
4. Only if all pass → GPU.

GPU-accelerated operations (via CuPy / `cupyx.scipy.ndimage`): patch extraction
and variance filtering, nearest-neighbor search, guided filter (fallback
formulation), and temporal smoothing of the transmission volume. **Airlight
estimation always runs on CPU** — `find_pairs` forces pairs to CPU NumPy and
`estimate_airlight` is pure NumPy. The temporal smoothing of the 1-D airlight
series also stays on CPU.

> GPU vs CPU may differ at floating-point rounding level. For exact CPU↔GPU
> parity, do not rely on it; treat CPU as the reference.

### Batching Semantics

`_iter_batches`
([pipeline/orchestration.py](../../../paloma/cleaning/dehazer/pipeline/orchestration.py)):

- `batch_size = None` → a single batch containing all (capped) files. This is
  the reference configuration: **global normalization and temporal smoothing
  span the entire sequence.**
- `batch_size = k` → files are split into `ceil(len/k)` contiguous groups; each
  group is loaded and processed **independently**. Consequently:
  - Global min/max are computed **per batch** (different normalization scale per batch).
  - Temporal Gaussian smoothing is applied **within each batch only** (no
    smoothing across batch boundaries).

Therefore output depends on `batch_size`. To reproduce a run, match it exactly
(default `None`).

### Determinism & Reproducibility Caveats

To obtain identical output, control every item below.

1. **Guided-filter backend (largest divergence source).** Presence of
   `cv2.ximgproc` switches between an OpenCV float32 implementation and the
   float64 box-filter fallback. Decide and document which is used; align the
   reference and the implementation. If unsure, **uninstall
   `opencv-contrib-python`** so both use the documented fallback formula.
2. **`max_patches` subsampling is unseeded.** `np.random.choice` without a seed
   makes patch selection (and thus $A$) nondeterministic. The default `None`
   avoids this; if you must cap, seed the global NumPy RNG identically.
3. **CPU vs GPU rounding.** `--gpu` can change low-order bits. Use CPU as the
   canonical reference.
4. **SciPy filter defaults.** Both `gaussian_filter1d` and `uniform_filter` rely
   on defaults `mode='reflect'`, `truncate=4.0` (Gaussian). An implementation
   using a different boundary mode (`nearest`, `constant`, `wrap`) or kernel
   truncation will diverge near edges.
5. **Nearest-neighbor tie-breaking.** Ties resolve via `argmin` (first minimum).
   A different NN library may break ties differently on degenerate data.
6. **Strict comparisons.** Variance filter uses `> variance_threshold`; pair
   acceptance uses `< nn_dist_threshold`. Match the strictness.
7. **Transmission clamp asymmetry.** The dehaze path clamps `t_initial` to
   `[0.01, 0.9]`. (The separate `validate` harness clamps to `[t_min_clip, 1.0]`
   — a simplified path; do not copy it into the main pipeline.)
8. **Global normalization.** The batch **must** be normalized by a single global
   min/max across all frames; per-frame normalization yields different output.
9. **HDU indices.** Inputs are read from **HDU 1**; outputs are written to **HDU 0**
   (PrimaryHDU). `validate`/simulation files are read from **HDU 0**.
10. **Skip-if-exists.** Pre-existing output files are skipped; clean the output
    directory before a fresh reproduction run.
11. **Frame ordering.** Alphabetical `sorted()` order defines the temporal axis.
12. **`num_frames` cap.** Only the first 10 (default) files participate.

## Code anchors

- `_resolve_gpu`, `_iter_batches` — [tess_dehazing/pipeline/orchestration.py](../../../paloma/cleaning/dehazer/pipeline/orchestration.py)
- `detect_gpu`, `is_gpu_free`, `to_gpu`, `to_cpu` — [tess_dehazing/core/backend.py](../../../paloma/cleaning/dehazer/core/backend.py)

## Ordering constraints

- Resolve GPU once at the start of `dehaze`, before loading batches.
- Treat CPU + fixed guided-filter backend + `batch_size=None` as the reference
  configuration for [08-verification](08-verification.md).

## Navigation

← [Prev: 06-recover-save](06-recover-save.md) · [Next: 08-verification](08-verification.md) →
