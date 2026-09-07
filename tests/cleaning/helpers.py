"""Shared helpers for cleaning / dehazer tests."""

from pathlib import Path

import numpy as np
from astropy.io import fits

# Small, fast config that still exercises every stage (patch pairing, guided
# filter, temporal smoothing). Overrides keep crops/radius tiny for speed.
CFG_KWARGS = {
    "num_frames": 4,
    "crop_bottom": 2,
    "crop_sides": 2,
    "patch_size": 9,
    "variance_threshold": 5e-5,
    "nn_dist_threshold": 0.3,
    "sigma_temporal": 1.5,
    "t_min_clip": 0.01,
    "guided_filter_radius": 3,
    "guided_filter_eps": 0.001,
    "num_iterations": 10,
    "fits_extension": 1,
    "max_patches": None,
    "batch_size": None,
}


def make_frame(height: int, width: int, t: int) -> np.ndarray:
    """Deterministic synthetic FFI-like frame with recurring texture + haze."""
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float64)
    freq = 2.0 * np.pi / 7.0
    texture = np.sin(xx * freq) * np.cos(yy * freq)
    scene = 0.5 + 0.3 * np.sin(xx * 0.05) + 0.2 * np.cos(yy * 0.04)
    haze = 0.1 * t
    base = scene + 0.15 * texture + haze
    rng = np.random.default_rng(1234 + t)
    base = base + rng.normal(0.0, 1e-3, size=base.shape)
    return (base * 1000.0 + 500.0).astype(np.float32)


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
