"""Slow ground-truth test for image subtraction."""

from pathlib import Path

import pytest

from paloma.image_subtraction import SubtractionConfig, subtract
from tests.image_subtraction.helpers import (
    SUBTRACTION_CFG_KWARGS,
    assert_residuals_match,
)

GROUNDTRUTH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "image_subtraction"
    / "groundtruth"
)
RAW = GROUNDTRUTH / "raw"
EXPECTED = GROUNDTRUTH / "expected" / "residuals"
REPO_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.slow


@pytest.mark.skipif(
    not (RAW.exists() and EXPECTED.exists()),
    reason="ground-truth image-subtraction fixtures missing",
)
def test_matches_reference_residuals(tmp_path):
    """Full OIS pipeline reproduces reference residuals within tolerance."""
    out = tmp_path / "actual"
    cfg_kwargs = {
        **SUBTRACTION_CFG_KWARGS,
        "blknum": 5,
        "num_iterations": 2,
        "num_frames": 5,
        "use_c_backend": True,
        "code_dir": str(REPO_ROOT / "build" / "code_dir"),
    }
    cfg = SubtractionConfig(**cfg_kwargs)
    subtract(str(RAW), str(out), cfg)
    n = assert_residuals_match(
        out / "04_residual_img",
        EXPECTED,
        rtol=1e-9,
        atol=1e-9,
    )
    assert n == 5
