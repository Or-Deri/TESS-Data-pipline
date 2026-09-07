"""Background estimation between iterative subtraction rounds."""

from __future__ import annotations

import os

from astropy.io import fits
from astropy.stats import SigmaClip
from photutils.background import Background2D, MedianBackground


def subtract_background(input_directory: str, output_directory: str) -> None:
    """Subtract residual background from preprocessed images in-place."""
    input_files = [f for f in os.listdir(input_directory) if f.endswith(".fits")]
    output_files = [f for f in os.listdir(output_directory) if f.endswith(".fits")]
    corresponding = [f for f in input_files if f in output_files]

    for name in corresponding:
        in_path = os.path.join(input_directory, name)
        out_path = os.path.join(output_directory, name)
        with fits.open(in_path) as in_hdul, fits.open(out_path, mode="update") as out_hdul:
            img = in_hdul[0].data
            sigma_clip = SigmaClip(sigma=3.0)
            bkg = Background2D(
                img,
                (32, 32),
                filter_size=(3, 3),
                sigma_clip=sigma_clip,
                bkg_estimator=MedianBackground(),
            )
            out_hdul[0].data = out_hdul[0].data - bkg.background
            out_hdul.flush()
