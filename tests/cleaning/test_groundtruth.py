"""Validate the 3-D pipeline against captured real-data ground truth.

``tests/data/cleaning/groundtruth/raw/`` holds 5 real TESS FFI frames;
``tests/data/cleaning/groundtruth/expected/`` holds the ``dehazed_3d__*.fits``
that the original dehazer produced from them. Full-resolution end-to-end
(a few minutes at ``guided_filter_radius=60`` on 2048x2048 frames); skipped
automatically if the FITS fixtures are missing.
"""

from pathlib import Path

import pytest

from paloma.cleaning.dehazer import DehazeConfig, dehaze
from tests.cleaning.helpers import assert_outputs_match

GROUNDTRUTH = (
    Path(__file__).resolve().parents[1] / "data" / "cleaning" / "groundtruth"
)
RAW_DIR = GROUNDTRUTH / "raw"
EXPECTED_DIR = GROUNDTRUTH / "expected"


@pytest.mark.skipif(
    not (RAW_DIR.exists() and EXPECTED_DIR.exists()),
    reason="ground-truth data (tests/data/cleaning/groundtruth) not present",
)
def test_matches_real_data_ground_truth(tmp_path):
    """Dehazing the raw frames reproduces the captured expected outputs.

    Uses the production defaults (``DehazeConfig()``) since that is what the
    expected FITS were generated with. Pixels must match to ``1e-9`` (the tiny
    residual comes from nondeterministic reduction ordering in the neighbour
    search, not from the algorithm). The captured ground-truth files use the
    original ``dehazed_3d__`` prefix; the current pipeline writes ``dehazed__``.
    """
    out_dir = tmp_path / "actual"
    dehaze(str(RAW_DIR), str(out_dir), DehazeConfig())

    n = assert_outputs_match(out_dir, EXPECTED_DIR, "dehazed__", "dehazed_3d__")
    assert n == 5
