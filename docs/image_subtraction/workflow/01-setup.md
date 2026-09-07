# Setup

## SubtractionConfig defaults

| Parameter | Default |
|---|---|
| kernel | 2 |
| stamp | 3 |
| order | 0 |
| nr_stars | 500 |
| blknum | 50 |
| num_iterations | 2 |
| random_seed | 0 |
| apply_data_quality_filter | True |

## Package layout

`paloma/image_subtraction/` — engine (not under `cleaning/`).

## CLI

```bash
python -m paloma.image_subtraction subtract \
  --input-dir tests/data/cleaning/groundtruth/raw \
  --output-dir results/subtracted \
  --blknum 5 --no-dquality-filter
```

## Stage API

```python
from paloma import ImageSubtractionStage, SubtractionRequest, CleaningStage

cleaning = CleaningStage("dehazer").run(CleaningRequest(...))
sub = ImageSubtractionStage("default", blknum=5, random_seed=0)
result = sub.run_after_cleaning(cleaning, "results/subtracted")
```
