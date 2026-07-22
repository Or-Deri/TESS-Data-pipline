# TESS Dehazer — Paloma cleaning engine

The dehazing engine behind Paloma's `"dehazer"` cleaner. It lives at
`paloma/cleaning/dehazer/` and is exposed to the pipeline by
`paloma.cleaning.dehazer_cleaner.DehazerCleaner`.

Remove scattered light from TESS Full Frame Images (FFIs) with a **3-D
spatio-temporal blind dehazing** pipeline based on Internal Patch Recurrence
(Bahat & Irani–style), extended across a time-ordered sector sequence.

The haze model per pixel is:

\[
I(x) = L(x)\,t(x) + A\,(1 - t(x))
\]

The pipeline estimates a global airlight \(A\) per frame from co-occurring
patches, recovers a transmission map \(t\), temporally smooths \(A\) and \(t\),
then recovers the clean scene \(L\).

## Requirements

- Python 3.9+
- Dependencies in the repo [`requirements.txt`](../../requirements.txt): NumPy,
  SciPy, Astropy, scikit-image, OpenCV, Matplotlib
- Optional: CuPy (for `--gpu`)

## Install

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .            # from the repo root
```

Run from the repo root so `python -m paloma.cleaning.dehazer` can import the package.

## Quick start

```bash
# Spatio-temporal dehazing: global normalization + temporal smoothing
python -m paloma.cleaning.dehazer dehaze \
  --input-dir /path/to/tess/sector \
  --output-dir /path/to/results

# Limit how many frames are loaded (default: 10)
python -m paloma.cleaning.dehazer dehaze \
  --input-dir /path/to/tess/sector \
  --output-dir /path/to/results \
  --num-frames 5

# Groundtruth fixtures shipped under data/
python -m paloma.cleaning.dehazer dehaze \
  --input-dir tests/data/groundtruth/raw \
  --output-dir results/ours \
  --num-frames 5
```

### Structured output layout

```bash
python -m paloma.cleaning.dehazer dehaze \
  --input-dir /path/to/tess/s0003-1-1 \
  --structured-layout \
  --output-base /path/to/project_root
```

Writes under:

```text
{output_base}/output_{sector}_GlobalNorm_Subfolders/{slug}/
```

With defaults, `{slug}` is `ps9_vt0.00005_nnd0.3`.

### Synthetic validation

```bash
python -m paloma.cleaning.dehazer simulate \
  --output-dir sim \
  --clean-fits clean.fits \
  --type cloud

python -m paloma.cleaning.dehazer validate \
  --sim-dir sim \
  --output-dir val
```

## Pipeline (3-D)

Ordering matters; the four algorithmic steps are not fused:

1. **Load & normalize** — sorted `*.fits`, HDU 1, float64, NaN→0, crop
   bottom 30 / sides 44, global min/max normalize to `[0, 1]`
2. **Estimate airlight** — high-variance 9×9 patches → unit L2 descriptors →
   brute-force NN pairs (`dist < 0.3`) → closed-form pairwise \(A\) →
   re-weighted average
3. **Smooth airlight** — 1-D Gaussian (`σ = 1.5`) over the \(A\) series
4. **Transmission & recover** — guided filter for \(t\), temporal smooth of
   the \(t\)-cube, invert the haze model, denormalize, save

Outputs:

| Artifact | Description |
|---|---|
| `dehazed__<original>.fits` | Float64 PrimaryHDU (HDU 0), original physical scale |
| `OUTPUT_LOCATION.txt` | Absolute paths + frame count for the run |

Existing output files are skipped (not overwritten). Clean the output directory
before a fresh reproduction run.

## Main CLI flags

| Flag | Default | Notes |
|---|---|---|
| `--input-dir` | required | Directory of input `*.fits` |
| `--output-dir` | — | Required unless `--structured-layout` |
| `--num-frames` | `10` | Max frames loaded (alphabetical order) |
| `--batch-size` | all | Frames per batch; affects global norm & temporal smooth |
| `--gpu` | off | Opt-in CuPy acceleration when a free GPU is available |
| `--patch-size` | `9` | Patch side length |
| `--variance-threshold` | `5e-5` | Min patch variance |
| `--nn-dist-threshold` | `0.3` | Max descriptor distance |
| `--sigma-temporal` | `1.5` | Temporal Gaussian σ |
| `--t-min-clip` | `0.01` | Transmission lower clamp |
| `--guided-filter-radius` | `60` | Guided / box filter radius |
| `--guided-filter-eps` | `0.001` | Guided filter ε |

Full parameter table: [`workflow/01-setup.md`](workflow/01-setup.md).

## Repository layout

The engine and its assets are spread across the Paloma repo:

```text
paloma/cleaning/
  dehazer_cleaner.py         # DehazerCleaner (Cleaner protocol adapter)
  dehazer/                   # The engine (this implementation)
    cli.py                   #   CLI entry (dehaze / simulate / validate)
    config.py                #   DehazeConfig defaults
    core/                    #   Numeric primitives (backend, patches, airlight,
                             #   guided_filter, transmission, recovery)
    io/                      #   FITS load/crop/save, normalize, output layout
    workflow/                #   Stage/Chain engine, WorkflowContext, dehazing stages
    pipeline/                #   dehaze orchestration + DehazePipeline facade
    strategies/              #   Pluggable Strategy layer (DehazingStrategy)
    evaluation/              #   Synthetic data + MSE / PSNR / SSIM
docs/dehazer/                # These docs (workflow/, PRD, thesis)
tests/                       # Test suite
  data/groundtruth/          # raw/ (input FFIs) + expected/ (captured ground truth)
results/                     # Local run outputs (transient)
```

## Documentation

The staged implementation contract lives under [`workflow/`](workflow/):

| Doc | Topic |
|---|---|
| [README](workflow/README.md) | Index + end-to-end ordering |
| [00 Foundations](workflow/00-foundations.md) | Haze model, glossary |
| [01 Setup](workflow/01-setup.md) | Stack, CLI, defaults |
| [02 Load & normalize](workflow/02-load-normalize.md) | FITS discovery, crop, global norm |
| [03 Estimate airlight](workflow/03-estimate-airlight.md) | Patches → pairs → \(A\) |
| [04 Smooth airlight](workflow/04-smooth-airlight.md) | Temporal Gaussian on \(A\) |
| [05 Transmission](workflow/05-transmission.md) | Guided filter + smooth \(t\) |
| [06 Recover & save](workflow/06-recover-save.md) | Recovery + output contract |
| [07 Ops](workflow/07-ops.md) | GPU, batching, determinism |
| [08 Verification](workflow/08-verification.md) | Acceptance criteria |
| [Appendix](workflow/appendix.md) | Thesis map, reference equivalence, function index |
| [Diagram](workflow/diagram.md) | Final workflow diagrams |

PRD: [`PRD_3D_MODE.md`](PRD_3D_MODE.md).  
Fixtures: [`tests/data/groundtruth/`](../../tests/data/groundtruth/).

## Testing

The `pytest` suite lives under [`tests/`](../../tests/):

```bash
pip install -e ".[dev]"      # from the repo root
pytest                 # everything, including the slow ground-truth test
pytest -m "not slow"   # skip the full-resolution real-data check
```

| Test | Scope |
|---|---|
| `test_pipeline.py` | `dehaze` determinism + the `DehazePipeline` facade matches `dehaze` (synthetic FITS, `1e-9`) |
| `test_groundtruth.py` | Full-res run on `tests/data/groundtruth/raw` matches captured `expected/` (marked `slow`) |
| `test_strategy.py` | Protocol / Strategy / Registry / `DehazingContext` layer |
| `test_workflow_engine.py` | `Stage` / `Chain` engine (composition, ordering, guards) |

## Reproducibility notes

- Frame order is alphabetical `sorted(*.fits)` — that defines the temporal axis.
- 3-D mode **must** use batch-wide global normalization (default).
- Guided-filter backend: OpenCV `ximgproc` (float32) vs the NumPy/SciPy
  float64 fallback can differ slightly. For matching the captured ground truth
  in [`tests/data/groundtruth/`](../../tests/data/groundtruth/), use plain `opencv-python` (no
  `opencv-contrib-python`).
- Leave `--max-patches` unset unless you intentionally seed NumPy; random
  subsampling is otherwise nondeterministic.
- CPU without `--gpu` and `batch_size=None` is the reference configuration.

## License / attribution

Algorithm from the M.Sc. thesis proposal *Removing Scattered Light from TESS
Full Frame Images using a Spatio-Temporal Patch Recurrence Prior* (Shachar
Fridman; supervisor Dr. Assaf Hoogi, Ariel University). Method adapted from
Bahat & Irani, *Blind Dehazing Using Internal Patch Recurrence* (ICCP 2016).
