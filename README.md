# Paloma — cleaning + stage shields

This package owns the **cleaning** area. Everything else is a *shield* (stub
stage / empty domain type) so the pipeline shape stays visible without
implementing other owners' work.

Design docs (from master, updated for this ownership):
[`architecture.md`](architecture.md) · [`prd_design_goals.md`](prd_design_goals.md)

| Area | Status |
|---|---|
| Cleaning (`Cleaner`, `CleaningStage`, dehazer) | **Implemented** |
| Ingestion, Validation, Detrending, Normalization, Feature Extraction, Classification | **Shield only** |

## Layout

```text
paloma/
  core/                 # PipelineStage, Cleaner protocol, types
  cleaning/             # OWNED: DehazerCleaner + dehazer engine
  stages/
    cleaning.py         # OWNED: CleaningStage
    shields.py          # Stub stages for all other steps
  config.py             # CleaningConfig
tests/                  # Cleaner / dehazer tests
  data/groundtruth/     # Dehazer fixtures (raw + expected)
docs/dehazer/           # Dehazer docs
results/                # Transient run outputs (gitignored)
architecture.md
prd_design_goals.md
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

First cleaner: `"dehazer"` — see [`docs/dehazer/README.md`](docs/dehazer/README.md).

> Dehazer cleans FFI *image cubes* (`CleaningRequest` → `CleaningResult`), not 1-D light curves.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```python
from paloma import CleaningStage, CleaningConfig, CleaningRequest

stage = CleaningStage.from_config(
    CleaningConfig(cleaner="dehazer", params={"num_frames": 5})
)
result = stage.run(
    CleaningRequest(
        input_dir="tests/data/groundtruth/raw",
        output_dir="results/cleaned",
    )
)
print(result.num_outputs, "frames cleaned ->", result.output_dir)
```

CLI: `python -m paloma.cleaning.dehazer dehaze ...`

## Development

```bash
pip install -e ".[dev]"
pytest tests            # add -m "not slow" to skip the full-res ground-truth check
```
