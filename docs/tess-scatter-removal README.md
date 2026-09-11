# TESS Scattered-Light Removal via Spatio-Temporal Patch Recurrence

A data-driven framework for removing scattered light from TESS Full Frame
Images (FFIs) by adapting blind image dehazing techniques using Internal Patch
Recurrence.

This is the implementation accompanying the M.Sc. thesis:

> **Removing Scattered Light in TESS Full Frame Images via Spatio-Temporal
> Patch Recurrence**
> Shachar Fridman, Ariel University, 2026

## Installation

```bash
python3 -m venv ~/tesis-venv
source ~/tesis-venv/bin/activate
pip install -r requirements.txt
```

> The venv is created in your home directory (`~/tesis-venv`) rather than
> inside the project folder because the project drive is FAT-formatted and
> does not support the symlinks that Python's `venv` requires.

### GPU acceleration (optional)

Install [CuPy](https://cupy.dev) matching your CUDA version for significantly
faster patch extraction, nearest-neighbor search, guided filtering, and
temporal smoothing:

```bash
# CUDA 12.x
pip install cupy-cuda12x

# CUDA 11.x
pip install cupy-cuda11x
```

GPU acceleration is **opt-in**.  Pass `--gpu` to any subcommand and the
pipeline will:

1. Check whether a CUDA device exists.
2. Check whether it is free (≥ 50 % VRAM available, compute load < 50 %).
3. Run on the GPU if both checks pass, or fall back to CPU automatically.

Without `--gpu` the pipeline runs on CPU exactly as before — no CuPy
installation required.

## Usage

The tool provides four subcommands: `dehaze`, `simulate`, `validate`, and `results`.

### Dehazing real TESS data

Run the 3-D spatio-temporal pipeline (recommended):

```bash
python -m tess_dehazing dehaze \
    --input-dir /path/to/tess/sector \
    --output-dir /path/to/results
```

Or use the 2-D per-frame mode:

```bash
python -m tess_dehazing dehaze \
    --input-dir /path/to/tess/sector \
    --output-dir /path/to/results \
    --mode 2d
```

Notebook-style folders (sector + parameters), as in `artical_finel.ipynb`:

- **3-D:** `{output_base}/output_{sector}_GlobalNorm_Subfolders/ps{patch}_vt{var}_nnd{nn}/`
- **2-D:** `{output_base}/CCD_{sector}_Results/ps{patch}_vt{var}_nnd{nn}/`

`{sector}` is taken from the input folder name if it looks like `s0003-1-1`, otherwise from the first FITS filename (`-s####-#-#-`).

**Where are the files?** With `--structured-layout`, dehazed FITS are **not** written next to your input FITS. They are under `{output_base}/output_{sector}_GlobalNorm_Subfolders/<params>/` (3-D) or `{output_base}/CCD_{sector}_Results/<params>/` (2-D). After each run, open `OUTPUT_LOCATION.txt` in that folder for the absolute path.

```bash
python -m tess_dehazing dehaze \
    --input-dir /path/to/tess/s0003-1-1 \
    --structured-layout \
    --output-base /path/to/project_root \
    --mode 3d
```

### Generating synthetic data

Create a contaminated sequence with an amorphous cloud:

```bash
python -m tess_dehazing simulate \
    --output-dir /path/to/sim_data \
    --clean-fits /path/to/clean_frame.fits \
    --type cloud
```

Or a null test (clean frames only):

```bash
python -m tess_dehazing simulate \
    --output-dir /path/to/null_data \
    --clean-fits /path/to/clean_frame.fits \
    --type null
```

### Results report (original vs dehazed)

After `dehaze`, print statistics and optionally save a figure. The default
**notebook** layout matches `artical_finel.ipynb`: one selected input frame,
**Original (Linear)** with a 1st--99th percentile stretch, then one column per
`--output-dir`, all dehazed panels sharing a **single global** `PowerNorm`
(sqrt, percentiles 0.5 and 99.8 on the concatenated dehazed data).

```bash
python -m tess_dehazing results \
    --input-dir /path/to/tess/sector \
    --output-dir /path/to/results_2d \
    --output-dir /path/to/results_3d \
    --plot /path/to/comparison.png \
    --no-show
```

Repeat `--output-dir` for each run you want beside the original (order matters).
`--frame-index` chooses which sorted FITS to show (default `1` = second file, as
in the notebook). For a 2xN overview of every frame using only the first output
folder, use `--plot-style grid`. On headless systems use `--no-show` when saving
`--plot`. For `grid` only, `--dehazed-display same` matches the original stretch.

Save the figure under the same structured tree as `dehaze` (match `--patch-size`,
`--variance-threshold`, `--nn-dist-threshold` to your run):

```bash
python -m tess_dehazing results \
    --input-dir /path/to/tess/sector \
    --output-dir /path/to/that/run/folder \
    --structured-plot \
    --output-base /path/to/project_root \
    --layout-mode 3d \
    --no-show
```

### Validation

Run the algorithm on simulated data and report MSE / PSNR / SSIM:

```bash
python -m tess_dehazing validate \
    --sim-dir /path/to/sim_data \
    --output-dir /path/to/validation_results
```

### Common flags

All subcommands accept optional algorithm-parameter overrides:

| Flag | Default | Description |
|------|---------|-------------|
| `--patch-size` | 9 | Patch side length (pixels) |
| `--variance-threshold` | 5e-5 | Minimum patch variance |
| `--nn-dist-threshold` | 0.3 | KDTree distance cutoff |
| `--sigma-temporal` | 1.5 | Temporal smoothing sigma |
| `--t-min-clip` | 0.01 | Transmission lower bound |
| `--guided-filter-radius` | 60 | Guided filter radius |
| `--guided-filter-eps` | 0.001 | Guided filter epsilon |
| `--num-frames` | 10 | Max frames to load |
| `--batch-size` | all at once | Frames processed per batch |
| `--max-patches` | unlimited | Cap on patches per frame |
| `--gpu` | off | Use GPU if a free CUDA device is found |

## Project structure

```
tess_dehazing/
    __init__.py        Package version
    __main__.py        python -m entry point
    cli.py             Argument parsing and subcommand dispatch
    config.py          DehazeConfig dataclass with defaults
    io.py              FITS loading, normalization, saving
    patches.py         Patch extraction and KDTree pair detection
    estimation.py      Airlight, transmission map, and scene recovery
    pipeline.py        2-D and 3-D pipeline orchestration
    simulation.py      Synthetic data generation and validation
    results_report.py  Print stats and plots for dehazed outputs
    output_layout.py   Sector + parameter output paths (notebook layout)
```

## Algorithm overview

1. **Data loading** -- TESS FFIs are read, cropped, and normalized to [0, 1].
   For the 3-D pipeline, a global min/max across all frames ensures physical
   consistency.

2. **Patch extraction** -- High-variance patches are identified, mean-subtracted,
   and L2-normalized to create descriptors invariant to the haze parameters.

3. **Co-occurrence matching** -- A KDTree finds nearest neighbors among
   normalized patch descriptors.  Pairs with small distance share the same
   underlying stellar structure but differ in scattered-light intensity.

4. **Airlight estimation** -- Each patch pair yields a closed-form estimate of
   the global scattered-light intensity A.  An iterative re-weighting scheme
   aggregates all pairwise estimates into a robust global value.

5. **Transmission map** -- The initial map t(x) = 1 - I(x)/A is refined with
   a guided filter to preserve stellar edges while smoothing the background.

6. **Temporal regularization (3-D only)** -- Both the airlight time-series and
   the transmission volume are smoothed along the temporal axis with a Gaussian
   kernel, enforcing physical continuity.

7. **Scene recovery** -- The haze model is inverted: L(x) = (I(x) - A) / t(x) + A.
