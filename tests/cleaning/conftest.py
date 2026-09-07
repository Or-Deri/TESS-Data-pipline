"""Pytest fixtures for cleaning / dehazer tests."""

from pathlib import Path

import pytest
from astropy.io import fits

from tests.cleaning.helpers import CFG_KWARGS, make_frame


@pytest.fixture(scope="session")
def synthetic_fits(tmp_path_factory) -> Path:
    """Create a directory of deterministic multi-HDU FITS frames (HDU 1 = data)."""
    input_dir = tmp_path_factory.mktemp("input_fits")
    height, width = 48, 52
    for t in range(CFG_KWARGS["num_frames"]):
        data = make_frame(height, width, t)
        hdul = fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(data)])
        hdul.writeto(input_dir / f"frame_{t:03d}.fits", overwrite=True)
    return input_dir


@pytest.fixture()
def cfg_kwargs() -> dict:
    return dict(CFG_KWARGS)
