# Ground-truth fixtures

Verification set for the 3-D pipeline (TESS sector s0003-2-1 FFIs).

| Path | Contents |
|---|---|
| [`raw/`](raw/) | Undehazed input FFIs (science HDU 1) |
| [`expected/`](expected/) | Reference `dehazed_3d__*.fits` from the original implementation |
| [`comparison_report.md`](comparison_report.md) | Bit-for-bit comparison notes from a prior reverse-engineering run |

## Reproduce comparison

```bash
# From repo root
python -m paloma.cleaning.dehazer dehaze \
  --input-dir tests/data/cleaning/groundtruth/raw \
  --output-dir results/ours \
  --num-frames 5
```

Compare `results/ours/dehazed__*.fits` to `tests/data/cleaning/groundtruth/expected/`
(the captured reference files keep their original `dehazed_3d__` prefix; match by
the frame name after the prefix). The `raw/` and `expected/` FITS fixtures are
tracked in git so `pytest -m slow` can run after a clone.
