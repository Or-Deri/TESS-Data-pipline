# Ground-truth fixtures (image subtraction)

Verification set for the OIS pipeline (TESS sector s0003-2-1, 5 FFIs).

| Path | Contents |
|---|---|
| [`raw/`](raw/) | Symlink to cleaning groundtruth raw FFIs |
| [`expected/residuals/`](expected/residuals/) | Reference `subtracted__*.fits` |
| [`expected/found_sources.csv`](expected/found_sources.csv) | Cross-matched source catalog (1922 rows) |
| [`expected/lightcurves.fits`](expected/lightcurves.fits) | Packed `TIME` / `FLUX` / `FLUX_ERR` for those sources |

```bash
pytest tests/image_subtraction
```

Residual fixtures were generated with `random.seed(0)`, `blknum=5`, `num_iterations=2`, `nr_stars=20`, and the compiled C OIS backend. The source catalog and packed light curves were captured from the original [`image-subtraction`](https://github.com/Astro-informatics-cipher-project/image-subtraction) detection / photometry (`src/core_science.py`, commit `456b2d2`) run on those residuals with `photutils==3.0.0`.

## Residuals

`expected/residuals/` is the authoritative OIS fixture. The pure-Python backend reproduces it to within float32 storage precision — the largest deviation across the five frames is `7.8e-3`, exactly half an ULP at the brightest pixel (~`1.4e5`). A compiled `build/a.out` is therefore no longer needed to validate the kernel fit.

## Catalog and light curves

`found_sources.csv` and `lightcurves.fits` are asserted in [`test_groundtruth.py`](../../../image_subtraction/test_groundtruth.py). Photometry follows the original estimator: sigma-clipped **mean** background under a 3-pixel aperture.

`photutils` is pinned to `3.0.0` in [`pyproject.toml`](../../../../pyproject.toml). Do not bump it without regenerating the catalog and light-curve fixtures: `DAOStarFinder` behaviour is part of the numerical contract.

To recapture catalog and light curves, re-run the original `findSources` / `crossMatch` / photometry from [`image-subtraction`](https://github.com/Astro-informatics-cipher-project/image-subtraction) `src/core_science.py` on `expected/residuals/` (same knobs: `threshold=50`, `fwhm=1.5`, `match_radius=3`, aperture radius 3, mean background). Copy the CSV over `expected/found_sources.csv` and pack the per-source light curves into `expected/lightcurves.fits`. Do not replace the residual FITS unless the OIS contract itself changed.
