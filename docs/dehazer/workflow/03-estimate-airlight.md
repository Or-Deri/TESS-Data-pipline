# 03 — Estimate Airlight (Step 1)

## Goal

For each frame in the normalized cube, estimate a scalar raw airlight $A_i$ via
high-variance patch extraction, co-occurrence pairing, closed-form pairwise
airlight, and iterative re-weighting.

## Inputs / outputs

| Kind | Detail |
|---|---|
| Input | Single normalized frame `cube[i]` (`float64`, $[0,1]$) |
| Input | `patch_size`, `variance_threshold`, `nn_dist_threshold`, `max_patches`, `num_iterations` |
| Output | Scalar $A_i \in [0,1]$ per frame; collected as `raw_airlights = [A_0, ..., A_{N-1}]` |

## Constants

| Field | Default |
|---|---:|
| `patch_size` | `9` |
| `variance_threshold` | `5e-5` |
| `nn_dist_threshold` | `0.3` |
| `max_patches` | `None` |
| `num_iterations` | `10` |
| NN chunk size | `4096` |
| Descriptor norm floor | `1e-6` |
| Pairwise denom floor | `10^{-6}` |
| Empty/invalid fallback $A$ | `0.5` |

## Algorithm

### Patch extraction (`extract_patches`)

[tess_dehazing/core/patches.py](../../../paloma/cleaning/dehazer/core/patches.py).

Inputs: a single normalized frame, `patch_size=9`, `variance_threshold=5e-5`,
`max_patches=None`.

1. Build an overlapping sliding-window view, **stride 1**, shape
   $(H-p+1,\, W-p+1,\, p,\, p)$ via `as_strided`
   (CPU/GPU) or `skimage.util.view_as_windows` fallback. Reshape to
   $(M, p, p)$ where $M = (H-p+1)(W-p+1)$.
2. `variances = var(patches, axis=(1,2))` (population variance, NumPy default `ddof=0`).
3. Keep indices where `variance > variance_threshold` (strictly greater).
4. *If* `max_patches` is set and exceeded: randomly subsample with
   `np.random.choice(num_kept, max_patches, replace=False)` — **unseeded**
   (nondeterministic; default `None` avoids this entirely).
5. For kept patches:
   - `means = mean(patch, axis=(1,2), keepdims=True)`
   - `centered = patch - means`
   - `flat = centered.reshape(K, p*p)`
   - `norms = ||flat||_2` per row
   - Drop rows with `norm <= 1e-6`.
   - `normalized = flat / norms[:, None]` (unit L2 vectors = **descriptors**).

Outputs: `original_patches` (raw $p\times p$ kept patches) and
`normalized_flat` (descriptors, shape $(K, p^2)$). Empty arrays if none qualify.

> **Thesis vs. code (descriptor normalization).** The thesis (Eq. 3.5–3.6)
> describes mean-subtraction followed by division by the patch **standard
> deviation** $\sigma_P$. The code divides the mean-subtracted patch by its
> **L2 norm** $\lVert\tilde P\rVert_2$, producing **unit** descriptors. The two
> differ only by the constant factor $\sqrt{w^2}=w$ (since
> $\sigma_P = \lVert\tilde P\rVert_2/\sqrt{w^2}$): the matching *direction* is
> identical, but the absolute descriptor scale — and hence the meaning of
> `nn_dist_threshold` — follows the **L2 (unit) convention**. Use unit
> descriptors for reproduction.

### Co-occurrence pairing (`find_pairs` → `find_nearest_neighbors`)

[tess_dehazing/core/patches.py](../../../paloma/cleaning/dehazer/core/patches.py) and
[tess_dehazing/core/backend.py](../../../paloma/cleaning/dehazer/core/backend.py).

> **Important — KD-Tree in theory, brute force in code.** The thesis (§3.2.1)
> describes a KD-Tree nearest-neighbor search. The code instead performs an
> **exact brute-force Euclidean nearest-neighbor search**
> (`find_nearest_neighbors`, chunked matmul). Both are *exact* NN, so a KD-Tree
> (`scipy.spatial.cKDTree`) would yield the same neighbors (modulo tie-breaking)
> — the result is equivalent, only the data structure differs.

Algorithm (`find_nearest_neighbors`, `chunk_size = 4096`):

1. `sq_norms = sum(descriptors**2, axis=1)` (≈ 1 since L2-normalized).
2. For each chunk of rows `[start:end]`, compute squared L2 distances to **all**
   descriptors:
   $$
   D_{ij} = \lVert d_i \rVert^2 + \lVert d_j \rVert^2 - 2\, d_i \cdot d_j
   $$
   via `sq_norms[start:end,None] + sq_norms[None,:] - 2*(chunk @ descriptors.T)`,
   then `maximum(D, 0)` for numerical stability.
3. Set the self-distance to `+inf` (`D[k, k+start] = inf`).
4. `nn_idx = argmin(D, axis=1)`; `nn_dist = sqrt(D[row, nn_idx])`.

Then in `find_pairs`:

5. Bring distances/indices/patches to CPU.
6. For every descriptor $i$ with `nn_dist[i] < nn_dist_threshold` (`0.3`,
   strictly less): form a pair from the **raw** patches $(p_i, p_{\text{nn}(i)})$.
7. **Order each pair so the higher-contrast patch is first:** if
   `std(p_i) >= std(p_{nn})` keep `(p_i, p_nn)` else swap. Result: `(p1, p2)`
   with `std(p1) >= std(p2)`.

> Because descriptors are unit vectors, $D = 2(1 - \cos\theta)$, so the cutoff
> `dist < 0.3` is equivalent to `cos θ > 0.955`.

Output: a Python list of `(p1, p2)` raw-patch tuples (always CPU NumPy).

### Closed-form pairwise airlight (`estimate_pairwise_airlight`)

[tess_dehazing/core/airlight.py](../../../paloma/cleaning/dehazer/core/airlight.py). Implements the
per-pair constraint of thesis Eq. 3.7,
$P_2(x) - A = \tfrac{t_2}{t_1}\,(P_1(x) - A)$, solved in closed form.

For a pair $(p_1, p_2)$ (higher-contrast first):

1. $\tilde p_1 = p_1 - \overline{p_1}$, $\tilde p_2 = p_2 - \overline{p_2}$.
2. $\mathrm{diff} = (\tilde p_2 - \tilde p_1)$ flattened.
3. $\mathrm{cross} = (p_1 \odot \tilde p_2 - p_2 \odot \tilde p_1)$ flattened
   ($\odot$ = elementwise).
4. $\mathrm{denom} = \mathrm{diff}\cdot\mathrm{diff}$; if $< 10^{-6}$ → return `None`.
5. $A = \dfrac{\mathrm{diff}\cdot\mathrm{cross}}{\mathrm{denom}}$.

**Why this works (derivation).** Assume within-patch constant transmission and
a shared latent pattern $R$:
$p_1 = t_1 R + A(1-t_1)$, $p_2 = t_2 R + A(1-t_2)$. Mean-subtraction removes the
constant $A(1-t)$ offset, giving $\tilde p_1 = t_1 \tilde R$, $\tilde p_2 = t_2 \tilde R$.
Substituting:

$$
\mathrm{cross} = p_1 \tilde p_2 - p_2 \tilde p_1 = A\,(t_2 - t_1)\,\tilde R, \qquad
\mathrm{diff} = (t_2 - t_1)\,\tilde R
$$

hence $\mathrm{cross} = A\,\mathrm{diff}$ and the least-squares ratio
$\langle \mathrm{diff}, \mathrm{cross}\rangle / \langle \mathrm{diff}, \mathrm{diff}\rangle$
recovers $A$ exactly (and robustly under noise).

### Iterative re-weighting (`estimate_airlight`)

[tess_dehazing/core/airlight.py](../../../paloma/cleaning/dehazer/core/airlight.py),
`num_iterations = 10`.

1. If `pairs` empty → return `0.5`.
2. Compute pairwise $A$ for all pairs; keep only those with
   `A is not None and 0.0 <= A <= 1.0` → list `pairwise_as`.
3. If none valid → return `0.5`.
4. Initialize `global_a = mean(pairwise_as)`.
5. Repeat `num_iterations` times:
   - For each pair $i$ (only while `i < len(pairwise_as)`):
     - Transmission lower bounds (per patch):
       $t_{\text{lb}} = \max_x\bigl(1 - p(x)/\max(A, 10^{-6})\bigr)$ via `_t_lower_bound`.
     - Skip the pair if `t_lb2 < 1e-6`.
     - Weight: $w_i = \bigl((t_{\text{lb}1} - t_{\text{lb}2})\,(t_{\text{lb}1}/t_{\text{lb}2} - 1)\bigr)^2$.
   - If `sum(weights) > 1e-6`: `global_a = np.average(valid_as, weights=weights)`
     (`valid_as` = the `pairwise_as` at the kept indices); else
     `global_a = mean(pairwise_as)`.
6. Return `clip(global_a, 0.0, 1.0)`.

> The weighting up-weights pairs with a large transmission **contrast** between
> the two patches (more informative about $A$) and down-weights near-equal pairs.
> This matches the thesis (§3.2.2, Eq. 3.7): each pair yields a least-squares
> estimate and the global $\hat A$ is a weighted average favoring pairs with
> larger transmission differences.

Output: scalar $A_i \in [0,1]$ for frame $i$. The 3-D Step 1 collects these into
`raw_airlights = [A_0, ..., A_{N-1}]`.

## Code anchors

- `extract_patches`, `find_pairs` — [tess_dehazing/core/patches.py](../../../paloma/cleaning/dehazer/core/patches.py)
- `find_nearest_neighbors` — [tess_dehazing/core/backend.py](../../../paloma/cleaning/dehazer/core/backend.py)
- `estimate_pairwise_airlight`, `_t_lower_bound`, `estimate_airlight` — [tess_dehazing/core/airlight.py](../../../paloma/cleaning/dehazer/core/airlight.py)

## Ordering constraints

- Estimate airlight for **all** frames before any temporal smoothing of $A$.
- Do not fuse this loop with transmission or recovery.
- Airlight estimation always runs on CPU (`find_pairs` forces pairs to CPU NumPy).

## Navigation

← [Prev: 02-load-normalize](02-load-normalize.md) · [Next: 04-smooth-airlight](04-smooth-airlight.md) →
