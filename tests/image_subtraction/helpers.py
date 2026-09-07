"""Shared helpers for image-subtraction tests."""

from pathlib import Path

import numpy as np
from astropy.io import fits

SUBTRACTION_CFG_KWARGS = {
    "blknum": 4,
    "num_iterations": 1,
    "nr_stars": 20,
    "random_seed": 0,
    "num_frames": 4,
    "apply_data_quality_filter": False,
    "kernel": 2,
    "stamp": 3,
    "order": 0,
}


def assert_residuals_match(
    dir_a: Path,
    dir_b: Path,
    prefix_a: str = "subtracted__",
    prefix_b: str = None,
    **kwargs,
) -> int:
    prefix_b = prefix_b or prefix_a
    names_a = sorted(p.name for p in Path(dir_a).glob(f"{prefix_a}*.fits"))
    assert names_a, f"no {prefix_a}*.fits in {dir_a}"
    suffixes_a = [n[len(prefix_a):] for n in names_a]
    suffixes_b = sorted(
        p.name[len(prefix_b):] for p in Path(dir_b).glob(f"{prefix_b}*.fits")
    )
    assert sorted(suffixes_a) == suffixes_b

    rtol = kwargs.get("rtol", 1e-5)
    atol = kwargs.get("atol", 1e-2)
    for suffix in suffixes_a:
        a = fits.getdata(Path(dir_a) / f"{prefix_a}{suffix}")
        b = fits.getdata(Path(dir_b) / f"{prefix_b}{suffix}")
        np.testing.assert_allclose(a, b, rtol=rtol, atol=atol, err_msg=suffix)
    return len(suffixes_a)
