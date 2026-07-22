# 04 — Smooth Airlight (Step 2)

## Goal

Temporally smooth the per-frame raw airlight series with a 1-D Gaussian so $A$
varies continuously across the sequence.

## Inputs / outputs

| Kind | Detail |
|---|---|
| Input | `raw_airlights` — length-$N$ list/array of scalars from Step 1 |
| Output | Smoothed series $A$ of length $N$ (CPU NumPy) |

## Constants

| Field | Default |
|---|---:|
| `sigma_temporal` | `1.5` |
| SciPy `order` | `0` |
| SciPy `mode` | `'reflect'` |
| SciPy `truncate` | `4.0` |
| Effective kernel half-width | `int(truncate*sigma + 0.5) = 6` for `sigma=1.5` |

## Algorithm

Temporal smoothing of the airlight series:

```text
A = scipy.ndimage.gaussian_filter1d(np.array(raw_airlights),
                                    sigma=sigma_temporal,   # 1.5
                                    axis=0)
```

- This is a **CPU** operation on a small 1-D array (stays on CPU even under `--gpu`).
- SciPy defaults apply and must be matched: `order=0`, `mode='reflect'`,
  `truncate=4.0`. The effective kernel half-width is `int(truncate*sigma + 0.5) = 6`
  for `sigma=1.5`.
- Corresponds to thesis Eq. 3.10: $A_{\text{smooth}}(t) = \mathrm{GaussianFilter1D}(A(t),\, \sigma=1.5)$.

## Code anchors

- Stage: `SmoothAirlight` in [`tess_dehazing/workflow/stages.py`](../../../paloma/cleaning/dehazer/workflow/stages.py) (Step 2 of `build_chain()`)
- `scipy.ndimage.gaussian_filter1d`

## Ordering constraints

- Run **after** raw $A_i$ exist for every frame in the batch.
- Run **before** any transmission-map estimation — transmission uses the
  **smoothed** $A$ series (code ordering, not thesis presentation order).
- With `batch_size=k`, smoothing is within-batch only (see [07-ops](07-ops.md#batching-semantics)).

## Navigation

← [Prev: 03-estimate-airlight](03-estimate-airlight.md) · [Next: 05-transmission](05-transmission.md) →
