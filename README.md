# Paloma — cleaning, image subtraction, + stage shields

This package owns **cleaning** and **image subtraction**. Other pipeline stages are *shields* (stubs).

Design docs: [`docs/architecture.md`](docs/architecture.md) · [`docs/design-goals.md`](docs/design-goals.md) · [`docs/`](docs/)

| Area | Status |
|---|---|
| Cleaning (`Cleaner`, `CleaningStage`, dehazer) | **Implemented** |
| Image subtraction (`Subtractor`, `ImageSubtractionStage`) | **Implemented** |
| Ingestion, Validation, Detrending, Normalization, Feature Extraction, Classification | **Shield only** |

## Layout

```text
paloma/
  core/                   # PipelineStage, Cleaner, Subtractor protocols
  cleaning/               # DehazerCleaner + dehazer engine
  image_subtraction/      # OIS engine (NOT a cleaner)
  stages/                 # CleaningStage, ImageSubtractionStage, shields
  config.py
  env.py                  # .env loader + PALOMA_* helpers
.env.example              # tracked template for all tunable params
.env                      # local copy (gitignored)
tests/
  cleaning/               # Dehazer / CleaningStage tests
  image_subtraction/      # OIS / ImageSubtractionStage tests
  data/
    cleaning/groundtruth/
    image_subtraction/groundtruth/
docs/
  architecture.md
  design-goals.md
  cleaning/dehazer/
  image_subtraction/
scripts/                  # Fixture / maintenance utilities
results/                  # Local run outputs (gitignored contents)
```

## Cleaners

```python
from paloma import BaseCleaner, register_cleaner, available_cleaners

@register_cleaner
class MyCleaner(BaseCleaner):
    name = "my_cleaner"
    def clean(self, request):
        ...

available_cleaners()  # -> ['dehazer', 'my_cleaner']
```

First cleaner: `"dehazer"` — see [`docs/cleaning/dehazer/README.md`](docs/cleaning/dehazer/README.md).

> Dehazer cleans FFI *image cubes* (`CleaningRequest` → `CleaningResult`), not 1-D light curves.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # local params (gitignored); edit as needed
```

## Configuration (`.env`)

All runtime tunables are declared in [`.env.example`](.env.example). Copy it to
`.env` (gitignored) and edit locally. Every key is prefixed `PALOMA_*`, documented
inline in the file, and wired through `paloma.env` → `*.from_env()`.

| Section | Keys | Consumed by |
|---|---|---|
| **1. Global I/O** | `PALOMA_INPUT_DIR`, `OUTPUT_DIR`, `OUTPUT_BASE`, `STRUCTURED_LAYOUT` | `paths_from_env()` · both CLIs |
| **2. Cleaning** | `PALOMA_CLEANER`, `PALOMA_DEHAZE_*` | `CleaningConfig.from_env()` · `DehazeConfig.from_env()` · `python -m paloma.cleaning.dehazer` |
| **3. Image subtraction** | `PALOMA_SUBTRACTOR`, `PALOMA_SUBTRACTION_*` | `ImageSubtractionConfig.from_env()` · `SubtractionConfig.from_env()` · `python -m paloma.image_subtraction` |

```python
from paloma import CleaningConfig, ImageSubtractionConfig, load_env, paths_from_env
from paloma.cleaning.dehazer import DehazeConfig
from paloma.image_subtraction import SubtractionConfig

load_env()                                  # reads repo-root .env
paths = paths_from_env()                    # I/O paths
cleaning = CleaningConfig.from_env()        # cleaner + dehaze params
subtraction = ImageSubtractionConfig.from_env()
dehaze = DehazeConfig.from_env()
ois = SubtractionConfig.from_env()
```

```bash
# CLI uses .env when flags are omitted; flags always win
python -m paloma.cleaning.dehazer dehaze
python -m paloma.image_subtraction subtract
```

Notes:

- Empty values mean “code default / `None`”.
- Booleans: `true`/`false` (also `1`/`0`, `yes`/`no`).
- Pairs: `x,y` (e.g. cutout center/size).
- Ints accept `0b…` / `0x…` (e.g. `PALOMA_SUBTRACTION_DATA_QUALITY_MASK`).
- **Tests do not read `.env`** — they use hardcoded fixtures / helpers. Only
  `tests/test_env.py` checks that `.env.example` stays in sync with the code.

## Usage

```python
from paloma import CleaningStage, CleaningConfig, CleaningRequest

stage = CleaningStage.from_config(CleaningConfig.from_env())
# or: CleaningConfig(cleaner="dehazer", params={"num_frames": 5})
result = stage.run(
    CleaningRequest(
        input_dir="tests/data/cleaning/groundtruth/raw",
        output_dir="results/cleaned",
    )
)
print(result.num_outputs, "frames cleaned ->", result.output_dir)
```

CLI: `python -m paloma.cleaning.dehazer dehaze ...`

## Image subtraction (after cleaning)

Image subtraction is **not** a cleaner. It runs via `ImageSubtractionStage` after cleaning:

```python
from paloma import (
    CleaningStage, CleaningConfig, CleaningRequest,
    ImageSubtractionStage, ImageSubtractionConfig,
)

cleaning = CleaningStage.from_config(CleaningConfig.from_env())
cleaned = cleaning.run(CleaningRequest(
    input_dir="tests/data/cleaning/groundtruth/raw",
    output_dir="results/cleaned",
))

subtraction = ImageSubtractionStage.from_config(ImageSubtractionConfig.from_env())
result = subtraction.run_after_cleaning(cleaned, "results/subtracted")
print(result.num_outputs, "residuals,", result.sources_csv)
```

Standalone: `python -m paloma.image_subtraction subtract ...` — see [`docs/image_subtraction/README.md`](docs/image_subtraction/README.md).

## Development

```bash
pip install -e ".[dev]"
pytest tests            # add -m "not slow" to skip the full-res ground-truth check
```
