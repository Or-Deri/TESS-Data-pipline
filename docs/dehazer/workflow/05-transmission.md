# 05 — Transmission (Step 3)

## Goal

Build a per-frame transmission map from the **smoothed** airlight via a guided
filter, then temporally smooth the stacked $t$-cube along the frame axis.

## Inputs / outputs

| Kind | Detail |
|---|---|
| Input | Normalized frame `cube[i]`; smoothed scalar $A_i$ |
| Input | `guided_filter_radius`, `guided_filter_eps`, `t_min_clip`, `sigma_temporal` |
| Intermediate | Per-frame refined $t_i$ (same device as input) |
| Output | Temporally smoothed `t_cube` shape $(N, H, W)$ |

## Constants

| Field | Default |
|---|---:|
| `guided_filter_radius` | `60` |
| `guided_filter_eps` | `0.001` |
| `t_min_clip` | `0.01` |
| Initial $t$ upper clamp | `0.9` (not `1.0`) |
| `A_safe` floor | `1e-6` |
| Box filter size | `2*radius+1 = 121` |
| `sigma_temporal` | `1.5` |

## Algorithm

### Transmission map (`recover_transmission_map`)

[tess_dehazing/core/transmission.py](../../../paloma/cleaning/dehazer/core/transmission.py). For each frame,
using the **smoothed** $A_i$:

1. `A_safe = max(A_i, 1e-6)`.
2. `t_initial = 1.0 - image / A_safe`.
3. **Clamp:** `t_initial = clip(t_initial, t_min_clip, 0.9)` — lower bound
   `0.01`, **upper bound `0.9`** (note: not `1.0`).
4. Refine: `t_refined = guided_filter(guide=image, src=t_initial, radius=60, eps=0.001)`.

**Guided filter** (`guided_filter`):

- **CPU fast path (preferred):** if `cv2.ximgproc.guidedFilter` is available,
  call it with `guide` and `src` cast to **float32**, `radius=60`, `eps=0.001`.
- **Fallback path (pure array, float64; also used on GPU):**
  with box filter $B_r(\cdot)$ = `uniform_filter(size = 2*radius+1 = 121)`
  (SciPy on CPU / cupyx on GPU; default `mode='reflect'`):

  $$
  \begin{aligned}
  \mu_I &= B_r(I), & \mu_p &= B_r(t_{\text{init}}), \\
  \mathrm{cov}_{Ip} &= B_r(I \cdot t_{\text{init}}) - \mu_I \mu_p, &
  \mathrm{var}_I &= B_r(I \cdot I) - \mu_I^2, \\
  a &= \frac{\mathrm{cov}_{Ip}}{\mathrm{var}_I + \varepsilon}, &
  b &= \mu_p - a\,\mu_I, \\
  t_{\text{refined}} &= B_r(a)\,I + B_r(b). &&
  \end{aligned}
  $$

> **Reproducibility:** the OpenCV and fallback paths differ slightly (algorithm
> detail + float32 vs float64). Pick one and document it. See
> [07-ops](07-ops.md#determinism--reproducibility-caveats).

Output: refined transmission map $t_i$ (same device as input).

### Temporal smoothing of the transmission volume

After all per-frame $t_i$ are stacked into `t_cube` of shape $(N, H, W)$:

```text
t_cube = gaussian_filter_temporal(t_cube, sigma=sigma_temporal)   # 1.5
```

`gaussian_filter_temporal` ([core/backend.py](../../../paloma/cleaning/dehazer/core/backend.py)) =
`gaussian_filter1d(t_cube, sigma=1.5, axis=0)` along the **temporal axis**
(SciPy on CPU, cupyx on GPU; same `mode='reflect'`, `truncate=4.0` defaults).
Spatial axes are untouched here. This is thesis Eq. 3.11,
$t_{\text{final}}(x,y,t) = \mathrm{GaussianFilter1D}(T_{\text{raw}}(x,y,t),\, \sigma=1.5)$.

## Code anchors

- `recover_transmission_map` — [tess_dehazing/core/transmission.py](../../../paloma/cleaning/dehazer/core/transmission.py)
- `_box_filter`, `guided_filter` — [tess_dehazing/core/guided_filter.py](../../../paloma/cleaning/dehazer/core/guided_filter.py)
- `gaussian_filter_temporal` — [tess_dehazing/core/backend.py](../../../paloma/cleaning/dehazer/core/backend.py)

## Ordering constraints

- Transmission maps for *all* frames are computed from the **already-smoothed**
  $A$ series **before** the transmission volume is smoothed.
- Do not use raw (pre-smooth) $A_i$ for production transmission — that is thesis
  presentation order; reproduce the **code** ordering.
- Do not fuse the per-frame transmission loop with recovery.

## Navigation

← [Prev: 04-smooth-airlight](04-smooth-airlight.md) · [Next: 06-recover-save](06-recover-save.md) →
