"""Shared helpers for image-subtraction tests."""

import csv
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


def assert_sources_match(
    actual: Path,
    expected: Path,
    rtol: float = 1e-9,
    atol: float = 1e-9,
) -> int:
    """Assert two ``found_sources.csv`` catalogs have the same rows."""

    def _load(path: Path) -> list[dict[str, str]]:
        with Path(path).open(newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    rows_a = _load(actual)
    rows_b = _load(expected)
    assert rows_a, f"no sources in {actual}"
    assert [tuple(r.keys()) for r in rows_a[:1]] == [tuple(r.keys()) for r in rows_b[:1]]
    assert len(rows_a) == len(rows_b), (
        f"source counts differ: {len(rows_a)} vs {len(rows_b)}"
    )

    numeric = [k for k in rows_a[0] if k != "index"]
    for i, (a, b) in enumerate(zip(rows_a, rows_b)):
        assert a["index"] == b["index"], f"row {i}: index {a['index']} != {b['index']}"
        for key in numeric:
            np.testing.assert_allclose(
                float(a[key]),
                float(b[key]),
                rtol=rtol,
                atol=atol,
                err_msg=f"row {i} {key}",
            )
    return len(rows_a)
