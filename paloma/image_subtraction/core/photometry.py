"""Aperture photometry and light-curve FITS output."""

from __future__ import annotations

import os

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from photutils.aperture import CircularAperture, aperture_photometry

from paloma.core.log import info, item

from ..io.layout import SUBTRACTED_PREFIX

# TESS TSTART is BTJD (BJD − this offset). Matches lightkurve's ``btjd`` format
# and the usual FFI keywords ``BJDREFI``/``BJDREFF``.
_TESS_BJDREF = 2457000.0

# Rotation/scale keywords that must not survive a WCS merge, so that the CD and
# PC conventions never appear in the same header.
_WCS_CONFLICT_KEYS = (
    "CD1_1",
    "CD1_2",
    "CD2_1",
    "CD2_2",
    "PC1_1",
    "PC1_2",
    "PC2_1",
    "PC2_2",
    "CDELT1",
    "CDELT2",
)


def tstart_to_jd(header: fits.Header) -> float:
    """Convert a TESS ``TSTART`` value (BTJD) to Julian Date."""
    tstart = float(header["TSTART"])
    bjdrefi = float(header.get("BJDREFI", _TESS_BJDREF))
    bjdreff = float(header.get("BJDREFF", 0.0))
    return tstart + bjdrefi + bjdreff


def propagate_wcs(dir_with_headers: str, dir_without_headers: str) -> None:
    """Copy the WCS from preprocessed frames onto their matching residuals.

    Residuals carry the ``subtracted__`` prefix, so they are paired with their
    source frame by name after stripping it. The WCS keywords are *merged* into
    the residual's existing header rather than replacing it: a bare
    ``WCS.to_header()`` carries no ``TSTART``, which
    :func:`measure_flux_timestamps` needs to build the light-curve time axis.
    """
    from .preprocess import _has_wcs

    sources = {
        name: os.path.join(dir_with_headers, name)
        for name in os.listdir(dir_with_headers)
        if name.endswith(".fits")
    }
    for name in sorted(os.listdir(dir_without_headers)):
        if not name.endswith(".fits"):
            continue
        stem = name
        if stem.startswith(SUBTRACTED_PREFIX):
            stem = stem[len(SUBTRACTED_PREFIX) :]
        source_path = sources.get(stem)
        if source_path is None:
            continue
        header = fits.getheader(source_path)
        if not _has_wcs(header):
            continue
        wcs_header = WCS(header).to_header(relax=True)
        with fits.open(os.path.join(dir_without_headers, name), mode="update") as hdul:
            target = hdul[0].header
            # Drop the old rotation/scale convention so a CD matrix and a PC
            # matrix never coexist in the merged header.
            for key in _WCS_CONFLICT_KEYS:
                target.remove(key, ignore_missing=True, remove_all=True)
            target.update(wcs_header)


def measure_flux_timestamps(apertures, aperture_rad: int, file_list: list[str]):
    flux, flux_err, time_stamps = [], [], []
    for path in file_list:
        img, head = fits.getdata(path, header=True)
        time_stamps.append(tstart_to_jd(head))
        _, median, _ = sigma_clipped_stats(img, sigma=3.0, maxiters=5)
        raw = aperture_photometry(img, apertures)
        # Median, to match the estimator used by OIS, ``background_subtract``
        # and kernel-star selection.
        bkg_sum = median * (np.pi * aperture_rad ** 2)
        flux.append(raw["aperture_sum"] - bkg_sum)
        flux_err.append(np.sqrt(np.abs(raw["aperture_sum"])))
    return flux, flux_err, time_stamps


def _header_str(header: fits.Header, key: str, default: str) -> str:
    val = header.get(key, default)
    if val is None or (isinstance(val, str) and not str(val).strip()):
        return default
    return str(val)


def write_lightcurves(
    flux_list,
    flux_err_list,
    time_stamps,
    source_list: list,
    ref_head: fits.Header,
    out_dir: str,
) -> list[str]:
    from .preprocess import _has_wcs

    os.makedirs(out_dir, exist_ok=True)
    nsrc = len(source_list)
    if nsrc == 0:
        return []

    camera = ref_head.get("CAMERA", 0)
    ccd = ref_head.get("CCD", 0)
    telescop = _header_str(ref_head, "TELESCOP", "TESS")
    mission = _header_str(ref_head, "MISSION", "TESS")
    times = np.asarray(time_stamps, dtype=np.float64)

    ras = decs = None
    if _has_wcs(ref_head):
        xs = np.asarray([xy[0] for xy in source_list], dtype=float)
        ys = np.asarray([xy[1] for xy in source_list], dtype=float)
        sky = SkyCoord.from_pixel(xs, ys, wcs=WCS(ref_head), mode="all")
        ras = np.asarray(sky.ra.deg)
        decs = np.asarray(sky.dec.deg)

    info(f"Writing {nsrc} light curves ...")
    outputs: list[str] = []
    report_every = max(1, nsrc // 5)
    for i, xy in enumerate(source_list):
        flux = np.asarray([row[i] for row in flux_list], dtype=np.float32)
        flux_err = np.asarray([row[i] for row in flux_err_list], dtype=np.float32)

        primary = fits.PrimaryHDU()
        primary.header["TELESCOP"] = telescop
        primary.header["MISSION"] = mission
        primary.header["CAMERA"] = camera
        primary.header["CCD"] = ccd
        primary.header["X_PIX"] = float(xy[0])
        primary.header["Y_PIX"] = float(xy[1])
        if ras is not None:
            primary.header["RA_OBJ"] = float(ras[i])
            primary.header["DEC_OBJ"] = float(decs[i])

        table = fits.BinTableHDU.from_columns(
            [
                fits.Column(name="TIME", format="D", unit="jd", array=times),
                fits.Column(name="FLUX", format="E", array=flux),
                fits.Column(name="FLUX_ERR", format="E", array=flux_err),
            ],
            name="LIGHTCURVE",
        )
        name = f"{camera}-{ccd}_{i:05d}_x{int(xy[0])}_y{int(xy[1])}.fits"
        out_path = os.path.join(out_dir, name)
        fits.HDUList([primary, table]).writeto(out_path, overwrite=True)
        outputs.append(out_path)
        if (i + 1) % report_every == 0 or i + 1 == nsrc:
            item(i + 1, nsrc, "light curves written")
    return outputs
