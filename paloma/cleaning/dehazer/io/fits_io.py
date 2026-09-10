"""FITS discovery, loading, cropping, batch normalization, and saving.

See ``README.md``.
"""

import glob
import os

import numpy as np
from astropy.io import fits

from paloma.core.log import info, item

#: Filename prefix for recovered/dehazed output FITS (``dehazed__<source>.fits``).
DEHAZED_PREFIX = "dehazed__"

#: WCS/structural FITS keywords dropped from the header we carry through the
#: dehazer. ``_crop_frame`` trims calibration rows/columns, which invalidates
#: any pixel-to-sky mapping baked into the source header (the image
#: subtraction preprocessor's ``_cutout_fits``/``align_image`` re-derive WCS
#: from scratch for raw, *uncropped* FFIs, and would mis-cutout an
#: already-cropped image if WCS keywords were left in place). Everything
#: else — ``EXPOSURE``, ``TSTART``/``TSTOP``, ``CAMERA``, ``CCD``,
#: ``DQUALITY``, ... — is preserved. Structural keys (NAXIS*, BITPIX, ...)
#: are dropped too since astropy recomputes them from the array on write.
_WCS_KEY_PREFIXES = (
    "CTYPE", "CRVAL", "CRPIX", "CDELT", "CUNIT", "CD1_", "CD2_",
    "PC1_", "PC2_", "PV1_", "PV2_", "A_", "B_", "AP_", "BP_",
)
_DROP_HEADER_KEYS = {
    "SIMPLE", "BITPIX", "NAXIS", "NAXIS1", "NAXIS2", "EXTEND",
    "PCOUNT", "GCOUNT", "XTENSION", "EXTNAME", "EXTVER",
    "WCSAXES", "LONPOLE", "LATPOLE", "RADESYS", "EQUINOX", "WCSNAME",
}


def _clean_header(header):
    """Copy ``header`` with WCS + structural keywords removed.

    Everything else (e.g. ``EXPOSURE``, ``TSTART``/``TSTOP``, ``CAMERA``,
    ``CCD``, ``DQUALITY``) is preserved so downstream stages (image
    subtraction) can read it back off the cleaned FITS.
    """
    cleaned = header.copy()
    for key in list(cleaned.keys()):
        if not key or key in _DROP_HEADER_KEYS or key.startswith(_WCS_KEY_PREFIXES):
            del cleaned[key]
    return cleaned


def normalize(frame, vmin, vmax):
    """Scale ``frame`` into [0, 1] using the given bounds (zeros if degenerate)."""
    rng = vmax - vmin
    if rng <= 0:
        return np.zeros_like(frame)
    return (frame - vmin) / rng


def denormalize(frame, vmin, vmax):
    """Invert :func:`normalize` back to the original physical scale."""
    return frame * (vmax - vmin) + vmin


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
    """Load one science HDU as a cropped, NaN-zeroed ``float64`` 2-D array.

    Returns ``(data, header)`` where ``header`` is the source HDU's header
    with WCS/structural keywords stripped (see :func:`_clean_header`) so
    non-positional metadata (``EXPOSURE``, ``TSTART``, ``DQUALITY``, ...)
    survives the round trip through the dehazer.
    """
    with fits.open(path) as hdul:
        hdu = hdul[cfg.fits_extension]
        data = hdu.data
        if data is None:
            raise ValueError(f"HDU {cfg.fits_extension} of {path!r} has no data")
        data = np.asarray(data, dtype=np.float64)
        header = _clean_header(hdu.header)
    data = np.nan_to_num(data)
    return _crop_frame(data, cfg.crop_bottom, cfg.crop_sides), header


def load_fits_directory(input_dir, cfg, files=None):
    """Load a batch of frames into a ``(N, H, W)`` float64 cube in [0, 1].

    Every frame is normalized by a single batch-wide min/max (global
    normalization), and each metadata entry stores that shared
    ``orig_min``/``orig_max`` so recovery can be denormalized consistently.
    """
    if files is None:
        files = get_fits_files(input_dir, cfg.num_frames)

    n_files = len(files)
    info(f"Loading {n_files} FITS files ...")
    frames = []
    filenames = []
    headers = []
    for i, path in enumerate(files):
        fname = os.path.basename(path)
        frame, header = load_single_fits(path, cfg)
        item(
            i + 1,
            n_files,
            f"{fname}  {frame.shape[0]}x{frame.shape[1]}  "
            f"[{np.min(frame):.2f}, {np.max(frame):.2f}]",
        )
        frames.append(frame)
        filenames.append(fname)
        headers.append(header)

    global_min = min(float(np.min(fr)) for fr in frames)
    global_max = max(float(np.max(fr)) for fr in frames)
    if global_max <= global_min:
        raise ValueError("Global max <= global min; cannot normalize batch")
    info(f"Normalizing to [0, 1] using global range [{global_min:.2f}, {global_max:.2f}]")

    normed = []
    metadata = []
    for fr, fn, hd in zip(frames, filenames, headers):
        n = normalize(fr, global_min, global_max)
        normed.append(n)
        metadata.append(
            {
                "orig_min": global_min,
                "orig_max": global_max,
                "filename": fn,
                "header": hd,
            }
        )

    return np.stack(normed, axis=0), metadata


def save_fits(data, path, header=None):
    """Write ``data`` as a single ``float64`` PrimaryHDU (HDU 0), overwriting.

    ``header`` (typically the cleaned header produced by
    :func:`load_single_fits`/:func:`load_fits_directory`) is carried over so
    non-positional metadata such as ``EXPOSURE``/``TSTART`` survives into the
    dehazed output; astropy recomputes ``NAXIS*``/``BITPIX`` from ``data``.
    """
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    hdu = fits.PrimaryHDU(np.asarray(data, dtype=np.float64), header=header)
    hdu.writeto(path, overwrite=True)
