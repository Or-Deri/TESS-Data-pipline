"""Ground-truth test for image subtraction."""

from pathlib import Path

import pytest

from paloma.image_subtraction import SubtractionConfig, subtract
from tests.image_subtraction.helpers import (
    SUBTRACTION_CFG_KWARGS,
    assert_lightcurves_match,
    assert_residuals_match,
    assert_sources_match,
)

GROUNDTRUTH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "image_subtraction"
    / "groundtruth"
)
RAW = GROUNDTRUTH / "raw"
EXPECTED = GROUNDTRUTH / "expected" / "residuals"
EXPECTED_SOURCES = GROUNDTRUTH / "expected" / "found_sources.csv"
EXPECTED_LIGHTCURVES = GROUNDTRUTH / "expected" / "lightcurves.fits"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _c_backend_available() -> bool:
    return (REPO_ROOT / "build" / "a.out").is_file() or (
        REPO_ROOT / "build" / "code_dir" / "a.out"
    ).is_file()


@pytest.mark.skipif(
    not (
        RAW.exists()
        and EXPECTED.exists()
        and EXPECTED_SOURCES.exists()
        and EXPECTED_LIGHTCURVES.exists()
    ),
    reason="ground-truth image-subtraction fixtures missing",
)
def test_matches_reference_outputs(tmp_path):
    """Full OIS pipeline reproduces residuals, source catalog, and light curves."""
    out = tmp_path / "actual"
    use_c = _c_backend_available()
    cfg_kwargs = {
        **SUBTRACTION_CFG_KWARGS,
        "blknum": 5,
        "num_iterations": 2,
        "num_frames": 5,
        "use_c_backend": use_c,
        "code_dir": str(REPO_ROOT / "build" / "code_dir"),
    }
    cfg = SubtractionConfig(**cfg_kwargs)
    subtract(str(RAW), str(out), cfg)
    # The residual fixtures were captured from the C backend. The pure-Python
    # OIS now reproduces them to within float32 storage precision: the largest
    # observed deviation over the fixture set is 7.8e-3, which is exactly half
    # an ULP at the brightest pixel (~1.4e5), and residuals are written as
    # float32. So a single tolerance covers both backends.
    n = assert_residuals_match(
        out / "04_residual_img",
        EXPECTED,
        rtol=1e-6,
        atol=1e-2,
    )
    assert n == 5

    actual_csv = out / "05_sources" / "found_sources.csv"
    n_src = assert_sources_match(actual_csv, EXPECTED_SOURCES)
    assert n_src > 0

    # Paloma residuals agree with the C fixtures to ~1e-2 counts; over a
    # 3-pixel aperture (~28 px) that is at most ~0.3 in flux.
    n_lc = assert_lightcurves_match(
        out / "06_lightcurves",
        EXPECTED_LIGHTCURVES,
        rtol=1e-4,
        atol=0.5,
    )
    assert n_lc == n_src
