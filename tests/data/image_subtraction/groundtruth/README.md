# Ground-truth fixtures (image subtraction)

Verification set for the OIS pipeline (TESS sector s0003-2-1, 5 FFIs).

| Path | Contents |
|---|---|
| [`raw/`](raw/) | Symlink to cleaning groundtruth raw FFIs |
| [`expected/residuals/`](expected/residuals/) | Reference `subtracted__*.fits` |
| [`expected/found_sources.csv`](expected/found_sources.csv) | Cross-matched source catalog |

```bash
python scripts/generate_image_subtraction_groundtruth.py
pytest tests/image_subtraction -m slow
```

Generated with `random.seed(0)`, `blknum=5`, `num_iterations=2`.
