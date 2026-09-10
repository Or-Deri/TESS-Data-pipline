# Ground-truth fixtures (cleaning)

Verification set for the dehazer (TESS sector s0003-2-1 FFIs).

| Path | Contents |
|---|---|
| [`raw/`](raw/) | Undehazed input FFIs (science HDU 1) |
| [`expected/`](expected/) | Reference `dehazed_3d__*.fits` |

```bash
python -m paloma.cleaning.dehazer dehaze \
  --input-dir tests/data/cleaning/groundtruth/raw \
  --output-dir results/ours \
  --num-frames 5

pytest tests/cleaning
```
