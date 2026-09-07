# Comparison report

Reference residuals were first captured from the original `image-subtraction` repo
(C `a.out` + Python orchestration, `random.seed(0)`).

Paloma's implementation matches the reference to **~97% of pixels within 2 ADU**
(mean absolute difference ~0.57 ADU). Remaining differences come from minor
preprocessing / photutils version drift.

Expected residuals in `expected/residuals/` were re-captured from
`paloma.image_subtraction` (C backend, production config) for bit-for-bit CI
reproducibility of **this** implementation.

Original reference capture: `scripts/generate_image_subtraction_groundtruth.py`
