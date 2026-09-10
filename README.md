# Paloma — cleaning + image subtraction

Two-stage TESS FFI pipeline:

```text
input FITS → Cleaning (dehazer) → cleaned FITS → Image Subtraction (OIS)
          → residuals / sources / light curves
```

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # local params (gitignored); edit as needed
```

## Configuration (`.env`)

All runtime tunables live in [`.env.example`](.env.example). Copy it to `.env` and edit.

Every key is `PALOMA_*`, documented inline, and loaded via `paloma.env` → `*.from_env()`.

| Section | Keys | Used by |
|---|---|---|
| Global I/O | `INPUT_DIR`, `OUTPUT_DIR`, `CLEANED_DIR`, `SUBTRACTED_DIR`, … | `Pipeline` |
| Cleaning | `PALOMA_CLEANER`, `PALOMA_DEHAZE_*` | dehazer |
| Image subtraction | `PALOMA_SUBTRACTOR`, `PALOMA_SUBTRACTION_*` | OIS |

Notes: empty = code default; bools `true`/`false`; pairs `x,y`; ints accept `0b…`/`0x…`. Tests do not read `.env` (except `tests/test_env.py`).

## Run the pipeline

```bash
python -m paloma
python -m paloma --input-dir path/to/fits --output-dir results
```

Default under `PALOMA_OUTPUT_DIR`: `cleaned/` then `subtracted/`.

```python
from paloma import Pipeline
result = Pipeline.from_env().run()
```

Stages stay chainable:

```python
from paloma import (
    CleaningStage, CleaningConfig, CleaningRequest,
    ImageSubtractionStage, ImageSubtractionConfig,
)

cleaned = CleaningStage.from_config(CleaningConfig.from_env()).run(
    CleaningRequest(input_dir="...", output_dir="results/cleaned")
)
sub = ImageSubtractionStage.from_config(ImageSubtractionConfig.from_env())
result = sub.run_after_cleaning(cleaned, "results/subtracted")
```

Single-stage CLIs:

```bash
python -m paloma.cleaning.dehazer dehaze
python -m paloma.image_subtraction subtract
```

## Tests

```bash
pytest tests
```

Ground-truth tests run with the rest of the suite when their FITS fixtures are present under `tests/data/`; otherwise they are skipped.

## Architecture

| Stage | Algorithm | Config | Contract |
|---|---|---|---|
| `CleaningStage` | `Cleaner` (`"dehazer"`) | `PALOMA_DEHAZE_*` | `CleaningRequest` → `CleaningResult` |
| `ImageSubtractionStage` | `Subtractor` (`"default"`) | `PALOMA_SUBTRACTION_*` | `SubtractionRequest` → `SubtractionResult` |

Chaining is directory-based: cleaning writes FITS; `SubtractionRequest.from_cleaning(...)` uses `cleaning.output_dir` as input. Returning `None` stops the pipeline.

Plug in new algos with `@register_cleaner` / `@register_subtractor` and select via `.env`.

Internal `>>` chains (shared engine: `paloma.core.chain`):

- **Dehazer:** `MoveCube → EstimateA → SmoothA → Transmission → Recover`
- **OIS:** `Preprocess → BuildReference → OptimalSubtract → Detect → LightCurves`

### Dehazer

Removes scattered light from TESS FFIs (`I = L·t + A·(1−t)`). Entry: `dehaze()` / CLI above. Package: `paloma/cleaning/dehazer/` (`runner`, `workflow`, `core`, `io`).

### Image subtraction

OIS after cleaning → residuals, `found_sources.csv`, light curves. Entry: `subtract()` / CLI above. Set `PALOMA_SUBTRACTION_USE_C_BACKEND=true` for compiled `a.out`, else pure Python.

## Layout

```text
paloma/
  pipeline.py             # Pipeline + CleaningStage + ImageSubtractionStage
  config.py  env.py
  core/                   # types, Cleaner/Subtractor, shared chain (>>)
  cleaning/               # DehazerCleaner + dehazer engine
  image_subtraction/      # DefaultSubtractor + OIS engine
.env.example
tests/
```
