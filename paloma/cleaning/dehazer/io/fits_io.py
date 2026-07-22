"""FITS discovery, loading, cropping, batch normalization, and saving.

See ``docs/workflow/02-load-normalize.md`` (load + global norm) and
``docs/workflow/06-recover-save.md`` (output contract).
"""

import glob
import os

import numpy as np
from astropy.io import fits

from .normalize import normalize

#: Filename prefix for recovered/dehazed output FITS (``dehazed__<source>.fits``).
DEHAZED_PREFIX = "dehazed__"


def get_fits_files(input_dir, num_frames=None):
    """Return alphabetically sorted ``*.fits`` paths, capped to ``num_frames``.

    The alphabetical order defines the temporal axis and must be preserved.
    """
    files = sorted(glob.glob(os.path.join(input_dir, "*.fits")))
    if not files:
        raise FileNotFoundError(f"No FITS files found in {input_dir!r}")
    if num_frames is not None:
        files = files[:num_frames]
    return files


def _crop_frame(data, crop_bottom, crop_sides):
    """Trim calibration edges: bottom rows and columns from each side."""
    h, w = data.shape
    return data[0 : h - crop_bottom, crop_sides : w - crop_sides]


def load_single_fits(path, cfg):
    """Load one science HDU as a cropped, NaN-zeroed ``float64`` 2-D array."""
    with fits.open(path) as hdul:
        data = hdul[cfg.fits_extension].data
        if data is None:
            raise ValueError(f"HDU {cfg.fits_extension} of {path!r} has no data")
        data = np.asarray(data, dtype=np.float64)
    data = np.nan_to_num(data)
    return _crop_frame(data, cfg.crop_bottom, cfg.crop_sides)


def load_fits_directory(input_dir, cfg, files=None):
    """Load a batch of frames into a ``(N, H, W)`` float64 cube in [0, 1].

    Every frame is normalized by a single batch-wide min/max (global
    normalization), and each metadata entry stores that shared
    ``orig_min``/``orig_max`` so recovery can be denormalized consistently.
    """
    if files is None:
        files = get_fits_files(input_dir, cfg.num_frames)

    print(f"Loading {len(files)} FITS files ...")
    frames = []
    filenames = []
    for i, path in enumerate(files):
        fname = os.path.basename(path)
        print(f"  [{i + 1}/{len(files)}] Loading {fname} ...", end=" ")
        frame = load_single_fits(path, cfg)
        print(f"shape={frame.shape}, range=[{np.min(frame):.2f}, {np.max(frame):.2f}]")
        frames.append(frame)
        filenames.append(fname)

    global_min = min(float(np.min(fr)) for fr in frames)
    global_max = max(float(np.max(fr)) for fr in frames)
    print(f"Normalizing globally: min={global_min:.2f}, max={global_max:.2f}")
    if global_max <= global_min:
        raise ValueError("Global max <= global min; cannot normalize batch")

    normed = []
    metadata = []
    for fr, fn in zip(frames, filenames):
        n = normalize(fr, global_min, global_max)
        normed.append(n)
        metadata.append(
            {"orig_min": global_min, "orig_max": global_max, "filename": fn}
        )
        print(f"  Normalized {fn}: [{np.min(n):.4f}, {np.max(n):.4f}]")

    print(f"Loaded and normalized {len(normed)} frames from {input_dir}")
    return np.stack(normed, axis=0), metadata


def save_fits(data, path):
    """Write ``data`` as a single ``float64`` PrimaryHDU (HDU 0), overwriting."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    hdu = fits.PrimaryHDU(np.asarray(data, dtype=np.float64))
    hdu.writeto(path, overwrite=True)
