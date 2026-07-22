# 08 — Verification & Acceptance

## Goal

Define how an implementation is accepted: direct array comparison, intermediate
golden diagnostics, and the `validate` regression harness.

## Inputs / outputs

| Kind | Detail |
|---|---|
| Input | Same input directory, identical parameters, clean output directories; matching guided-filter backend |
| Output | Pass/fail against `np.allclose` and/or MSE/PSNR/SSIM tolerances |

## Constants

| Criterion | Value |
|---|---|
| Primary `allclose` | `rtol=1e-5`, `atol=1e-6` |
| Cloud simulate seed | `np.random.seed(999)` |
| Soft regression tolerances (example) | PSNR within ~0.1 dB; SSIM within ~1e-3 |

## Algorithm

An implementation is accepted when **all** of the following hold.

### Direct array comparison (primary)

Run both implementations on the **same** input directory with **identical**
parameters and a **clean** output directory, then for each frame compare the
saved arrays:

- **Acceptance:** `np.allclose(ref, new, rtol=1e-5, atol=1e-6)` on the
  denormalized output for every frame, **when the guided-filter backend matches**.
- If backends differ (OpenCV vs fallback), expect larger deviations concentrated
  in smooth background regions; compare structure with the metrics below instead.

### Intermediate "golden values" (diagnostic)

The pipeline prints these; capture and compare them to localize divergence:

- Per-frame **raw airlights** (`raw_airlights`) and the **smoothed** `A` series.
- `Max smoothing delta` for `A`.
- Transmission **initial** and **refined** min/max/mean per frame.
- Smoothed **t-cube** min/max/mean.
- Per-frame final `result range=[min, max]`.

Matching the raw and smoothed $A$ arrays first isolates Steps 1–2 from the
guided-filter/transmission stage.

### Automated regression suite (`pytest`)

The repository guards the engine with a `pytest` suite ([tests/](../../tests)):

| Test file | What it checks |
|---|---|
| [test_pipeline.py](../../tests/test_pipeline.py) | `dehaze` is deterministic for a fixed config, and the `DehazePipeline` facade reproduces `dehaze` output on synthetic FITS to `rtol=atol=1e-9`. |
| [test_groundtruth.py](../../tests/test_groundtruth.py) | Full-resolution end-to-end run on `tests/data/groundtruth/raw` matches the captured `tests/data/groundtruth/expected` FITS. Marked `slow`; auto-skipped if the fixtures are absent. |
| [test_strategy.py](../../tests/test_strategy.py) | The Strategy layer (`available_strategies() == ["default"]`, factory, registry guards, `DehazingContext`) and that the strategy wrapper is a no-op over `dehaze`. |
| [test_workflow_engine.py](../../tests/test_workflow_engine.py) | The `Stage`/`Chain` engine: composition via `>>`, ordering, `requires` guards, `WorkflowContext.prefix`. |

`assert_outputs_match` matches frames by the source name *after* the prefix, so
it compares the current `dehazed__` output against the reference `dehazed_3d__`
fixtures. Run everything (including the slow test) with `pytest`; exclude the
slow test with `pytest -m "not slow"`.

### Quantitative metrics via `validate` (regression)

Use the bundled harness ([evaluation/simulation.py](../../../paloma/cleaning/dehazer/evaluation/simulation.py)) as an
end-to-end check on controlled data:

```bash
python -m paloma.cleaning.dehazer simulate --output-dir sim --clean-fits clean.fits --type cloud
python -m paloma.cleaning.dehazer validate --sim-dir sim --output-dir val
```

- `simulate --type cloud` seeds its cloud texture with `np.random.seed(999)`
  (the moving-envelope cloud is deterministic given the same clean frame).
- `evaluate_metrics` reports **MSE**, **PSNR** (`skimage.metrics.peak_signal_noise_ratio`),
  and **SSIM** (`structural_similarity`), each with `data_range = gt.max() - gt.min()`,
  comparing the recovered middle frame to the normalized ground truth.
- **Acceptance:** MSE/PSNR/SSIM reproduce the reference within small tolerance
  (e.g. PSNR within ~0.1 dB, SSIM within ~1e-3) on the same backend.

**Reference values (thesis Table 5.1, synthetic "Amorphous Cloud" dataset).**
The thesis reports the following on its synthetic benchmark; a correct
implementation on a comparable clean frame and matching backend should land near
these:

| Metric | Reported value | Ideal |
|---|---|---|
| PSNR | **44.62 dB** | $\infty$ |
| SSIM | **0.979** | 1.0 |
| MSE | $\mathbf{3 \times 10^{-5}}$ | 0 |

The simulation behind this benchmark (thesis §4.1.1, code
`generate_amorphous_cloud`) builds the stray-light cube as
$I_{\text{syn}}(x,\tau) = I_{\text{clean}}(x) + S(x,\tau) + \eta(x)$ with a
coherent-noise texture (`gaussian_filter`, $\sigma=30$), a moving spatial
envelope, peak intensity ≈ **20×** the median background, and $N=10$ frames.
Exact numbers depend on the chosen clean frame and the guided-filter backend.

> Note: `validate` uses HDU 0 sim files and a transmission clamp of
> `[t_min_clip, 1.0]`; it is a *validation convenience path* and is intentionally
> simpler than the production transmission clamp `[0.01, 0.9]` in
> [05-transmission](05-transmission.md).

## Code anchors

- `run_simulation`, `generate_amorphous_cloud`, `generate_null_test`, `evaluate_metrics`, `run_validation` — [tess_dehazing/evaluation/simulation.py](../../../paloma/cleaning/dehazer/evaluation/simulation.py)
- Automated suite: [tests/](../../tests) (`conftest.py`, `test_pipeline.py`, `test_groundtruth.py`, `test_strategy.py`, `test_workflow_engine.py`)
- Ground-truth fixtures: [tests/data/groundtruth/](../../tests/data/groundtruth/)

## Ordering constraints

- Align guided-filter backend and clean the output directory before primary
  `allclose` checks ([07-ops](07-ops.md)).
- Prefer comparing raw/smoothed $A$ before diagnosing transmission divergence.

## Navigation

← [Prev: 07-ops](07-ops.md) · [Next: appendix](appendix.md) →
