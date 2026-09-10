"""Ground-truth test for image subtraction."""

from pathlib import Path

import pytest

from paloma.image_subtraction import SubtractionConfig, subtract
from tests.image_subtraction.helpers import (
    SUBTRACTION_CFG_KWARGS,
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
REPO_ROOT = Path(__file__).resolve().parents[2]


def _c_backend_available() -> bool:
    return (REPO_ROOT / "build" / "a.out").is_file() or (
        REPO_ROOT / "build" / "code_dir" / "a.out"
    ).is_file()


@pytest.mark.skipif(
    not (RAW.exists() and EXPECTED.exists() and EXPECTED_SOURCES.exists()),
    reason="ground-truth image-subtraction fixtures missing",
)
def test_matches_reference_residuals(tmp_path):
    """Full OIS pipeline reproduces reference residuals and source catalog."""
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
    # Fixtures were captured from the C backend (bit-identical at 1e-9).
    # Without ``build/a.out`` the pipeline uses Python OIS, which is close
    # but not identical (helper defaults: rtol=1e-5, atol=1e-2).
    tol = {"rtol": 1e-9, "atol": 1e-9} if use_c else {}
    n = assert_residuals_match(
        out / "04_residual_img",
        EXPECTED,
        **tol,
    )
    assert n == 5

    actual_csv = out / "05_sources" / "found_sources.csv"
    assert actual_csv.is_file(), f"missing source catalog at {actual_csv}"
    header = actual_csv.read_text(encoding="utf-8").splitlines()[0].strip()
    assert header == "index,ra,dec"
    if use_c:
        n_src = assert_sources_match(actual_csv, EXPECTED_SOURCES)
        assert n_src > 0
    else:
        # Python OIS residuals differ, so the catalog is not bit-identical.
        n_src = sum(1 for line in actual_csv.read_text(encoding="utf-8").splitlines()[1:] if line.strip())
        assert n_src > 0
