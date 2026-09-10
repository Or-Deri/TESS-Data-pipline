"""Shared helpers for cleaning tests."""

from pathlib import Path

import numpy as np
from astropy.io import fits


def _read(path: Path) -> np.ndarray:
    with fits.open(path) as hdul:
        return np.asarray(hdul[0].data, dtype=np.float64)


def assert_outputs_match(
    dir_a: Path, dir_b: Path, prefix_a: str = "dehazed__", prefix_b: str = None
) -> int:
    """Assert both dirs hold the same dehazed frames with identical pixels.

    Frames are matched by the source name *after* the prefix, so the two dirs may
    use different prefixes (e.g. the refactored ``dehazed__`` vs the reference
    package's ``dehazed_3d__``). Returns the number of frames compared.
    """
    prefix_b = prefix_b or prefix_a
    names_a = sorted(p.name for p in Path(dir_a).glob(f"{prefix_a}*.fits"))
    names_b = sorted(p.name for p in Path(dir_b).glob(f"{prefix_b}*.fits"))
    assert names_a, f"no {prefix_a}*.fits produced in {dir_a}"

    suffixes_a = sorted(n[len(prefix_a):] for n in names_a)
    suffixes_b = sorted(n[len(prefix_b):] for n in names_b)
    assert suffixes_a == suffixes_b, (
        f"output frame sets differ:\n{suffixes_a}\n{suffixes_b}"
    )

    for suffix in suffixes_a:
        a = _read(Path(dir_a) / f"{prefix_a}{suffix}")
        b = _read(Path(dir_b) / f"{prefix_b}{suffix}")
        assert a.shape == b.shape, f"{suffix}: shape {a.shape} != {b.shape}"
        np.testing.assert_allclose(
            a, b, rtol=1e-9, atol=1e-9,
            err_msg=f"{suffix}: refactored output differs from the original algorithm",
        )
    return len(suffixes_a)
