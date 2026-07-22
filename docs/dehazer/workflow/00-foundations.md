# 00 — Foundations

## Goal

Define the product purpose, haze image-formation model, goals, and notation
needed before implementing any pipeline stage.

## Inputs / outputs

N/A — conceptual stage. Downstream stages consume the symbols defined in the
glossary ($I$, $L$, $t$, $A$, patch, cube, etc.).

## Constants

None specific to this stage (see [01-setup](01-setup.md) for `DehazeConfig`
defaults).

## Algorithm

### Metadata

| Field | Value |
|---|---|
| Product | TESS Scattered-Light Removal via Spatio-Temporal Patch Recurrence |
| Package version | `0.1.0` (see [tess_dehazing/__init__.py](../../../paloma/cleaning/dehazer/__init__.py)) |
| Thesis | *Removing Scattered Light from TESS Full Frame Images using a Spatio-Temporal Patch Recurrence Prior* |
| Author / supervisor | Shachar Fridman; supervisor Dr. Assaf Hoogi |
| Institution | Ariel University, Department of Computer Science (M.Sc. thesis proposal, December 29, 2025) |
| Pipeline documented | The single spatio-temporal dehazing pipeline (`dehaze`); no mode flag |
| Canonical package | `paloma.cleaning.dehazer` (the dehazing engine) |
| Numeric pin | Captured ground truth under `tests/data/groundtruth/expected/` (see [08 Verification](08-verification.md)) |
| Primary language | Python 3 |
| Entry point | `python -m paloma.cleaning.dehazer` |

This workflow documents the **dehazing engine** at `paloma.cleaning.dehazer`. It
was refactored from an original flat `tess_dehazing` implementation; during that
refactor it was validated bit-for-bit against the original (`run_3d`). That
original code copy is no longer bundled — numeric output is now pinned by the
captured ground-truth FITS under `tests/data/groundtruth/expected/`.

### Purpose & Background

TESS (Transiting Exoplanet Survey Satellite) Full Frame Images (FFIs) are
contaminated by **scattered light** (stray light from the Earth and Moon) that
appears as a smooth, time-varying, additive glow over the star field. This
glow degrades photometry and masks faint structure.

The product treats scattered-light removal as a **blind image dehazing**
problem, adapting the *Internal Patch Recurrence* prior (Bahat & Irani-style
blind dehazing) to astronomical sequences. The central observation:

- The same small image structures (patches) recur across an image and across
  a time sequence.
- A recurring structure appears under **different amounts of scattered light**.
- Comparing two recurrences of the same structure that differ only in haze
  level yields a closed-form estimate of the global scattered-light intensity.

The **3-D mode** extends this from a single frame to a *time-ordered sequence*
from one TESS sector: all frames are normalized on a single physical scale and
the recovered haze parameters are smoothed along the temporal axis to enforce
physical continuity between consecutive frames.

#### Scientific context

TESS (launched April 2018) observes from a highly elliptical High-Earth Orbit
(HEO) in 2:1 resonance with the Moon; light from the Earth and Moon scatters off
the camera lens-hood optics onto the detectors. The resulting background is
**structured, high-amplitude, and varies in both space and time**, and can
exceed the flux of faint stars by an order of magnitude — defeating simple
median/polynomial background subtraction.

The method is **unsupervised** (no clean ground truth is required) and is framed
as blind source separation. It adapts the *Internal Patch Recurrence* prior of
Bahat & Irani (ICCP 2016) rather than the popular Dark Channel Prior (He et al.,
2011), which fails on astronomical data because the sky is predominantly dark and
stars are sparse point sources. In space the scattered light is primarily
**additive** (see the simulation model in [08-verification](08-verification.md)).

### Goals & Non-Goals

#### Goals

- **G1 — Reproducibility.** An implementation following this document must
  produce dehazed FITS files (`dehazed__*.fits`) that match the reference
  output within tight numerical tolerance (see [08-verification](08-verification.md)).
- **G2 — Completeness.** Every algorithmic step, constant, default, and
  ordering decision that affects output is specified.
- **G3 — Determinism.** All sources of nondeterminism are enumerated so the
  implementer can either match or consciously diverge from them.
- **G4 — Technology transparency.** Every third-party library and the exact
  function used from it is documented.

#### Non-Goals

- `simulate` and `validate` are described only to the extent that `validate` is
  the recommended acceptance harness.
- Performance tuning, GPU kernel optimization, and UI/plotting aesthetics are
  out of scope beyond what changes numeric output.

### Glossary & Notation

| Symbol / term | Meaning |
|---|---|
| $I(x)$ | Observed (contaminated) pixel intensity at location $x$, normalized to $[0,1]$ |
| $L(x)$ | Latent clean scene radiance to be recovered |
| $t(x)$ | Transmission map: fraction of scene light reaching the sensor ($t \in (0,1]$) |
| $A$ | Airlight — the global scattered-light intensity (a scalar per frame) |
| Patch | A square $p \times p$ window of pixels (default $p = 9$) |
| Descriptor | A mean-subtracted, L2-normalized flattened patch vector used for matching |
| Co-occurring pair | Two patches whose descriptors are nearest neighbors and close enough (distance $< 0.3$) |
| Frame | One FITS image in the sequence |
| Cube / volume | The stacked sequence of frames, shape $(N, H, W)$ |
| Sector | A TESS observation sector id like `s0003-1-1` |
| FFI | Full Frame Image |
| $\hat A$ | Estimated airlight value (thesis notation) |
| $\hat L(x)$ | Recovered (dehazed) scene radiance |
| $B(x)$ | Additive background term $A(1-t(x))$ |
| $\mu_P,\ \sigma_P$ | Patch mean and standard deviation (contrast) |
| $w$ | Thesis symbol for patch width (= PRD $p$ = `patch_size`) |
| $I_{\text{global}}$ | Globally normalized image cube (thesis) |
| $A_{\text{smooth}}(t)$ | Temporally smoothed airlight series (thesis) |
| $T_{\text{raw}},\ t_{\text{final}}$ | Raw / temporally smoothed transmission volume (thesis) |
| $\sigma_\tau$ | Temporal Gaussian sigma (= `sigma_temporal` = 1.5) |
| $v_{\min}, v_{\max}$ | Global (batch-wide) intensity bounds for normalization |

Notation follows the thesis *List of Symbols*; this workflow writes $p$ for the patch
side length where the thesis uses $w$.

### The Haze Model (Mathematics)

The forward model (thesis Eq. 3.4; optical scattering model of Narasimhan &
Nayar, 2003), applied per pixel $x$ on normalized data:

$$
I(x) = L(x)\,t(x) + A\,\bigl(1 - t(x)\bigr)
$$

- $A$ is a **scalar per frame** (global scattered-light intensity, thesis $\hat A$).
- $t(x) \in (0, 1]$ is the per-pixel transmission.
- The additive background term is $B(x) = A\,(1 - t(x))$; in space the scattered
  light is predominantly additive.
- Recovery inverts the model:

$$
L(x) = \frac{I(x) - A}{t(x)} + A
$$

with $t$ clamped from below by `t_min_clip` to avoid division blow-up, and the
result clipped to $[0, 1]$.

The 3-D mode adds the assumption that $A$ and $t$ vary **smoothly in time**,
realized as Gaussian smoothing along the frame axis.

## Code anchors

- Package version: [`tess_dehazing/__init__.py`](../../../paloma/cleaning/dehazer/__init__.py)
- Orchestration overview: [`tess_dehazing/pipeline/orchestration.py`](../../../paloma/cleaning/dehazer/pipeline/orchestration.py)

## Ordering constraints

None — read before implementing later stages. Thesis ↔ stage mapping lives in
the [appendix](appendix.md#thesis-mapping).

## Navigation

← [Prev: workflow index](README.md) · [Next: 01-setup](01-setup.md) →
