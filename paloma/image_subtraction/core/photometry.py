"""Aperture photometry and light-curve FITS output."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from photutils.aperture import CircularAperture, aperture_photometry

from paloma.core.log import info, item

# TESS TSTART is BTJD (BJD − this offset). Matches lightkurve's ``btjd`` format
# and the usual FFI keywords ``BJDREFI``/``BJDREFF``.
_TESS_BJDREF = 2457000.0


def tstart_to_jd(header: fits.Header) -> float:
    """Convert a TESS ``TSTART`` value (BTJD) to Julian Date."""
    tstart = float(header["TSTART"])
    bjdrefi = float(header.get("BJDREFI", _TESS_BJDREF))
    bjdreff = float(header.get("BJDREFF", 0.0))
    return tstart + bjdrefi + bjdreff


def propagate_wcs(dir_with_headers: str, dir_without_headers: str) -> None:
    from .preprocess import _has_wcs

    headers_files = sorted(f for f in os.listdir(dir_with_headers) if f.endswith(".fits"))
    no_headers_files = sorted(f for f in os.listdir(dir_without_headers) if f.endswith(".fits"))
    for header_file, no_header_file in zip(headers_files, no_headers_files):
        if Path(header_file).stem != Path(no_header_file).stem:
            continue
        header_path = os.path.join(dir_with_headers, header_file)
        no_header_path = os.path.join(dir_without_headers, no_header_file)
        _, header = fits.getdata(header_path, header=True)
        if not _has_wcs(header):
            continue
        wcs = WCS(header)
        no_img, _ = fits.getdata(no_header_path, header=True)
        fits.PrimaryHDU(no_img, header=wcs.to_header(relax=True)).writeto(
            no_header_path, overwrite=True
        )


def measure_flux_timestamps(apertures, aperture_rad: int, file_list: list[str]):
    flux, flux_err, time_stamps = [], [], []
    for path in file_list:
        img, head = fits.getdata(path, header=True)
        time_stamps.append(tstart_to_jd(head))
        mean, median, std = sigma_clipped_stats(img, sigma=3.0, maxiters=5)
        raw = aperture_photometry(img, apertures)
        bkg_sum = mean * (np.pi * aperture_rad ** 2)
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
