# 01 — Setup

## Goal

Document the technology stack, package layout, CLI contract, and canonical
`DehazeConfig` defaults required to run and reproduce the 3-D pipeline.

## Inputs / outputs

| Kind | Detail |
|---|---|
| Input | CLI flags / `DehazeConfig` fields |
| Output | A fully populated `DehazeConfig` passed to `dehaze` |

## Constants

All defaults from [tess_dehazing/config.py](../../../paloma/cleaning/dehazer/config.py)
(`DehazeConfig` dataclass). These values are the canonical defaults; matching
them is required for reproduction.

| Field | Type | Default | Used in step | Meaning |
|---|---|---:|---|---|
| `patch_size` | int | `9` | Patch extraction | Square patch side length (px) |
| `variance_threshold` | float | `5e-5` | Patch extraction | Min patch variance to keep |
| `nn_dist_threshold` | float | `0.3` | Pairing | Max NN descriptor distance |
| `sigma_temporal` | float | `1.5` | Temporal smoothing | Gaussian sigma (frames) |
| `t_min_clip` | float | `0.01` | Transmission, recovery | Lower clamp on $t$ |
| `guided_filter_radius` | int | `60` | Transmission | Guided/box filter radius |
| `guided_filter_eps` | float | `0.001` | Transmission | Guided filter regularization |
| `num_frames` | int | `10` | Loading | Max frames loaded from dir |
| `batch_size` | Optional[int] | `None` | Batching | Frames/batch (`None` = all) |
| `use_gpu` | bool | `False` | All | GPU opt-in |
| `crop_bottom` | int | `30` | Loading | Rows trimmed from bottom |
| `crop_sides` | int | `44` | Loading | Columns trimmed each side |
| `max_patches` | Optional[int] | `None` | Patch extraction | Cap per frame (`None` = unlimited) |
| `num_iterations` | int | `10` | Airlight | Re-weighting iterations |
| `fits_extension` | int | `1` | Loading | HDU index for science data |

Quick reference:
`patch_size=9`, `variance_threshold=5e-5`, `nn_dist_threshold=0.3`,
`sigma_temporal=1.5`, `t_min_clip=0.01`, `guided_filter_radius=60`,
`guided_filter_eps=0.001`, `num_frames=10`, `batch_size=None`, `use_gpu=False`,
`crop_bottom=30`, `crop_sides=44`, `max_patches=None`, `num_iterations=10`,
`fits_extension=1`.

## Algorithm

### Technology Stack & Dependencies

From [requirements.txt](../../requirements.txt):

| Library | Used for (3-D mode) | Exact API surface relied on |
|---|---|---|
| **NumPy** | All array math, stacking, stride tricks, dot products, clipping, `np.random.choice` (only if `max_patches` set) | `np.float64`, `np.nan_to_num`, `np.var`, `np.linalg.norm`, `np.dot`, `np.average`, `np.clip`, `np.stack`, `np.lib.stride_tricks.as_strided` |
| **Astropy** | FITS reading/writing | `astropy.io.fits.open`, `fits.PrimaryHDU`, `HDUList.writeto` |
| **SciPy** | Temporal smoothing, box filter | `scipy.ndimage.gaussian_filter1d`, `scipy.ndimage.uniform_filter` |
| **OpenCV** (`opencv-python`, ideally `opencv-contrib-python`) | Fast guided filter on CPU | `cv2.ximgproc.guidedFilter` (optional — see caveat) |
| **scikit-image** | Fallback sliding window; image-quality metrics in `validate` | `skimage.util.view_as_windows`, `skimage.metrics.peak_signal_noise_ratio`, `structural_similarity` |
| **Matplotlib** | Listed in `requirements.txt` but **not imported** by the `tess_dehazing` package (legacy plotting dependency; nothing in the dehaze/simulate/validate path uses it) | — |
| **CuPy** *(optional)* | GPU acceleration of array ops | `cupy`, `cupyx.scipy.ndimage` |

> **Critical caveat — guided filter backend.** `cv2.ximgproc.guidedFilter`
> exists only when `opencv-contrib-python` is installed. When present, the CPU
> path uses it in **float32**; when absent, the code falls back to a pure
> NumPy/SciPy box-filter formulation in **float64**. These two backends produce
> slightly different transmission maps and therefore slightly different output.
> **For exact reproduction, fix the backend** (see [07-ops](07-ops.md#determinism--reproducibility-caveats)).

GPU acceleration is strictly **opt-in** (`--gpu`). Without it, no CuPy install
is required and the pipeline runs identically on CPU.

### System Architecture

#### Package layout (canonical `tess_dehazing`)

```
tess_dehazing/
    __init__.py            Package version (0.1.0) + public API exports
    __main__.py            `python -m paloma.cleaning.dehazer` entry point
    cli.py                 Argument parsing + subcommand dispatch
    config.py              DehazeConfig dataclass (all defaults)
    core/                  Device-agnostic numeric primitives
        backend.py         GPU detection + GPU-agnostic array helpers
        patches.py         Patch extraction + co-occurrence pairing
        airlight.py        Pairwise + iterative airlight estimation
        guided_filter.py   Edge-preserving guided filter
        transmission.py    Transmission-map estimation
        recovery.py        Haze-model inversion (scene recovery)
    io/                    FITS + normalization + output paths
        fits_io.py         FITS discovery, load, crop, batch norm, save
        normalize.py       normalize / denormalize
        layout.py          Structured (notebook-style) output paths
    workflow/              The chain framework + the algorithm's stages
        engine.py          Stage / Chain / FunctionStage / as_stage / timed
        context.py         WorkflowContext (shared mutable state)
        stages.py          Concrete Steps 1-4 as composable stages (3-D)
    pipeline/              Orchestration
        orchestration.py   dehaze + GPU resolve, batching, markers
        fluent.py          DehazePipeline (fluent facade)
    strategies/           Pluggable Strategy layer (embed in a larger pipeline)
        base.py            Dehazer protocol + BaseDehazer + DehazeResult
        registry.py        register_strategy / create_dehazer / available_strategies
        context.py         DehazingContext
        dehazing.py        DehazingStrategy ("default")
    evaluation/           Verification path
        simulation.py      Synthetic data + MSE/PSNR/SSIM validation
```

The numeric core (`core/`, `io/`) is behaviourally unchanged; the algorithm is
expressed as a **chain of stages** (`workflow/`) that `pipeline/` runs once per
batch. See the [chainable stage API](README.md#chainable-stage-api) in the
workflow index.

#### Design-pattern layer (`tess_dehazing/strategies/`)

The algorithms are exposed behind a small, stable surface so a **surrounding
pipeline can select and run a dehazer without importing any internals**:

- `Dehazer` — a `typing.Protocol` (structural interface: `label` + `run`).
- `BaseDehazer` — Strategy base (Template Method: `run` = `_run` then collect a
  `DehazeResult`); concrete `DehazingStrategy` (`"default"`).
- `register_strategy` / `create_dehazer` / `available_strategies` — registry +
  factory; new algorithms self-register by label with no other code changes.
- `DehazingContext` — holds the active strategy and delegates `execute(...)`.
- `DehazeResult` — label, input/output dirs, and produced FITS paths.

```python
from paloma.cleaning.dehazer import DehazingContext, DehazeConfig

result = DehazingContext.default().execute(in_dir, out_dir, DehazeConfig())
print(result.num_outputs, "frames ->", result.output_dir)
```

The original code also had a Strategy-pattern variant (its own `DehazingContext`
+ `2d`/`3d` strategies); that copy is no longer bundled. The engine's Strategy
layer above differs in that its single `DehazingStrategy` simply wraps `dehaze`
(Template Method), so there is no duplicated pipeline body to keep in sync.

### CLI Contract (3-D)

Defined in [tess_dehazing/cli.py](../../../paloma/cleaning/dehazer/cli.py) (`build_parser`,
`_add_common_args`, `_handle_dehaze`). `_handle_dehaze` dispatches through the
strategy layer: `DehazingContext.default().execute(...)`. There is a single
built-in dehazer, so no mode selection flag is needed.

#### Invocation

```bash
python -m paloma.cleaning.dehazer dehaze \
    --input-dir /path/to/tess/sector \
    --output-dir /path/to/results
```

Structured (notebook-style) layout:

```bash
python -m paloma.cleaning.dehazer dehaze \
    --input-dir /path/to/tess/s0003-1-1 \
    --structured-layout \
    --output-base /path/to/project_root
```

#### `dehaze` arguments

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--input-dir` | str | **required** | Directory of input `*.fits` |
| `--output-dir` | str | `None` | Required unless `--structured-layout` |
| `--output-base` | str | `None` | Parent dir; **required** with `--structured-layout` |
| `--structured-layout` | flag | off | Build `output_<sector>_GlobalNorm_Subfolders/<slug>/` |
| `--patch-size` | int | `9` | |
| `--variance-threshold` | float | `5e-5` | |
| `--nn-dist-threshold` | float | `0.3` | Distance cutoff (see [03-estimate-airlight](03-estimate-airlight.md)) |
| `--sigma-temporal` | float | `1.5` | Temporal Gaussian sigma |
| `--t-min-clip` | float | `0.01` | Transmission lower clamp |
| `--guided-filter-radius` | int | `60` | |
| `--guided-filter-eps` | float | `0.001` | |
| `--num-frames` | int | `10` | Max frames loaded |
| `--max-patches` | int | `None` | Cap per frame (random subsample) |
| `--batch-size` | int | `None` | Frames per batch (`None` = all) |
| `--gpu` | flag | off | Use GPU if free CUDA device found |

`_build_config` overrides a default `DehazeConfig` only for flags that are not
`None`; `--gpu` sets `cfg.use_gpu = True`.

### `simulate` and `validate` subcommands (verification path)

Two auxiliary subcommands support the acceptance harness
([08-verification](08-verification.md)); they are dispatched by `_handle_simulate`
and `_handle_validate` and delegate to
[`tess_dehazing/evaluation/simulation.py`](../../../paloma/cleaning/dehazer/evaluation/simulation.py).

`simulate` — generate a synthetic sequence (`run_simulation`):

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--output-dir` | str | **required** | Where `sim_*.fits` + `ground_truth.fits` are written |
| `--clean-fits` | str | **required** | Clean frame (read from HDU 0) to contaminate |
| `--type` | `cloud`\|`null` | `cloud` | `cloud` = moving amorphous stray light (seed `999`); `null` = copies of the clean frame |
| `--num-frames` | int | `10` | Frames to synthesize |

`validate` — dehaze a synthetic sequence and score the middle frame
(`run_validation`); it accepts all of `_add_common_args`:

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--sim-dir` | str | **required** | Directory of `sim_*.fits` + `ground_truth.fits` |
| `--output-dir` | str | **required** | Where `recovered_mid.fits` is written |
| *common args* | — | — | Same tuning flags as `dehaze` (`--patch-size`, `--variance-threshold`, …, `--gpu`) |

> There is **no `results` subcommand** in `tess_dehazing`; only `dehaze`,
> `simulate`, and `validate` are registered by `build_parser`.

## Code anchors

- [`tess_dehazing/cli.py`](../../../paloma/cleaning/dehazer/cli.py) — `build_parser`, `_build_config`, `_handle_dehaze`, `_handle_simulate`, `_handle_validate`
- [`tess_dehazing/config.py`](../../../paloma/cleaning/dehazer/config.py) — `DehazeConfig`
- [`tess_dehazing/strategies/`](../../../paloma/cleaning/dehazer/strategies) — `Dehazer`, `BaseDehazer`, `DehazingContext`, `create_dehazer`, `available_strategies`
- [`tess_dehazing/workflow/`](../../../paloma/cleaning/dehazer/workflow) — `Stage`, `Chain`, `WorkflowContext`, stages, `build_chain`
- [`tess_dehazing/core/`](../../../paloma/cleaning/dehazer/core) — numeric primitives (backend, patches, airlight, guided_filter, transmission, recovery)
- [`requirements.txt`](../../requirements.txt) · [`requirements-dev.txt`](../../requirements-dev.txt)

## Ordering constraints

Build config before loading data. GPU opt-in is resolved later in
[07-ops](07-ops.md) at the start of `dehaze`.

## Navigation

← [Prev: 00-foundations](00-foundations.md) · [Next: 02-load-normalize](02-load-normalize.md) →
