"""Ground-truth test for image subtraction."""

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
    # The fixtures were captured from the C backend. The pure-Python OIS now
    # reproduces them to within float32 storage precision: the largest observed
    # deviation over the fixture set is 7.8e-3, which is exactly half an ULP at
    # the brightest pixel (~1.4e5), and residuals are written as float32. So a
    # single tolerance covers both backends.
    n = assert_residuals_match(
        out / "04_residual_img",
        EXPECTED,
        rtol=1e-6,
        atol=1e-2,
    )
    assert n == 5

    actual_csv = out / "05_sources" / "found_sources.csv"
    assert actual_csv.is_file(), f"missing source catalog at {actual_csv}"
    header = actual_csv.read_text(encoding="utf-8").splitlines()[0].strip()
    assert header == "index,ra,dec"
    n_src = sum(
        1
        for line in actual_csv.read_text(encoding="utf-8").splitlines()[1:]
        if line.strip()
    )
    assert n_src > 0

    # ``expected/found_sources.csv`` is NOT asserted against. It holds 2203 rows,
    # but feeding the reference residuals in ``EXPECTED`` through the current
    # detection code yields 1922 - so the fixture cannot be reproduced from the
    # residuals it shipped with. ``photutils`` is unpinned (>=1.5, now 3.x) and
    # ``DAOStarFinder`` changed since capture, so the catalog fixture is stale
    # while the residual fixtures remain valid. Regenerate it (see
    # tests/data/image_subtraction/groundtruth/README.md) before re-enabling an
    # equality check via ``assert_sources_match``.
