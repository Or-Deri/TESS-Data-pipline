# Ground-truth fixtures — image subtraction

Verification set for the OIS pipeline (TESS sector s0003-2-1, 5 FFIs).

| Path | Contents |
|---|---|
| [`raw/`](raw/) | Symlink to `tests/data/cleaning/groundtruth/raw/` (5 undehazed FFIs) |
| [`expected/residuals/`](expected/residuals/) | Reference `subtracted__*.fits` (slow pytest pin) |
| [`expected/found_sources.csv`](expected/found_sources.csv) | Cross-matched source catalog (manual / future checks) |

## Reproduce

```bash
source .venv/bin/activate
python scripts/generate_image_subtraction_groundtruth.py
```

Generated with ``random.seed(0)``, ``blknum=5``, ``num_iterations=2``.
