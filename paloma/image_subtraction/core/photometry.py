"""Aperture photometry and light-curve FITS output."""

from __future__ import annotations

import os
from pathlib import Path

import lightkurve as lk
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.time import Time
from astropy.wcs import WCS
from photutils.aperture import CircularAperture, aperture_photometry


def propagate_wcs(dir_with_headers: str, dir_without_headers: str) -> None:
    headers_files = sorted(f for f in os.listdir(dir_with_headers) if f.endswith(".fits"))
    no_headers_files = sorted(f for f in os.listdir(dir_without_headers) if f.endswith(".fits"))
    for header_file, no_header_file in zip(headers_files, no_headers_files):
        if Path(header_file).stem != Path(no_header_file).stem:
            continue
        header_path = os.path.join(dir_with_headers, header_file)
        no_header_path = os.path.join(dir_without_headers, no_header_file)
        _, header = fits.getdata(header_path, header=True)
        wcs = WCS(header)
        no_img, _ = fits.getdata(no_header_path, header=True)
        fits.PrimaryHDU(no_img, header=wcs.to_header(relax=True)).writeto(
            no_header_path, overwrite=True
        )


def measure_flux_timestamps(apertures, aperture_rad: int, file_list: list[str]):
    flux, flux_err, time_stamps = [], [], []
    for path in file_list:
        img, head = fits.getdata(path, header=True)
        time_stamps.append(Time(head["TSTART"], format="btjd").jd)
        mean, median, std = sigma_clipped_stats(img, sigma=3.0, maxiters=5)
        raw = aperture_photometry(img, apertures)
        bkg_sum = mean * (np.pi * aperture_rad ** 2)
        flux.append(raw["aperture_sum"] - bkg_sum)
        flux_err.append(np.sqrt(np.abs(raw["aperture_sum"])))
    return flux, flux_err, time_stamps


def write_lightcurves(
    flux_list,
    flux_err_list,
    time_stamps,
    source_list: list,
    ref_head: fits.Header,
    out_dir: str,
) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    ref_wcs = WCS(ref_head)
    outputs: list[str] = []
    for i, xy in enumerate(source_list):
        flux = [row[i] for row in flux_list]
        flux_err = [row[i] for row in flux_err_list]
        lc = lk.LightCurve(time=time_stamps, flux=flux, flux_err=flux_err)
        fits_lc = lc.to_fits()
        fits_lc[0].header["CCD"] = ref_head.get("CCD", 0)
        fits_lc[0].header["CAMERA"] = ref_head.get("CAMERA", 0)
        fits_lc[0].header["TELESCOP"] = ref_head.get("TELESCOP", "")
        sky = SkyCoord.from_pixel(xy[0], xy[1], wcs=ref_wcs, mode="all")
        ra_dec = sky.to_string("decimal").split(" ")
        fits_lc[0].header["RA_OBJ"] = ra_dec[0]
        fits_lc[0].header["DEC_OBJ"] = ra_dec[1]
        name = (
            f"{fits_lc[0].header['CAMERA']}-{fits_lc[0].header['CCD']}_"
            f"{i:05d}_x{int(xy[0])}_y{int(xy[1])}.fits"
        )
        out_path = os.path.join(out_dir, name)
        fits_lc.writeto(out_path, overwrite=True)
        outputs.append(out_path)
    return outputs
