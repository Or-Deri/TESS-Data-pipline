"""FITS I/O helpers for the subtraction pipeline."""

from __future__ import annotations

import glob
import os

from astropy.io import fits
from astropy.stats import sigma_clipped_stats

SUBTRACTED_PREFIX = "subtracted__"


def get_fits_files(input_dir: str, num_frames: int | None = None) -> list[str]:
    files = sorted(glob.glob(os.path.join(input_dir, "*.fits")))
    if num_frames is not None:
        files = files[:num_frames]
    return files


def save_fits(data, header, path: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fits.PrimaryHDU(data, header=header).writeto(path, overwrite=True)
    return path


def background_subtract(img):
    _, median, _ = sigma_clipped_stats(img, sigma=3.0, maxiters=5)
    return img - median, float(median)
