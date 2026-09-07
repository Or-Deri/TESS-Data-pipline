"""Kernel star selection for OIS."""

from __future__ import annotations

import random
from glob import glob
from pathlib import Path

import numpy as np
from photutils.aperture import CircularAperture, aperture_photometry


def select_kernel_stars(
    ref_dir: str,
    img: np.ndarray,
    img_median: float,
    number_stars: int,
    aperture_rad: int,
    *,
    random_seed: int = 0,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Return (x, y, count) kernel stars for OIS fitting."""
    starlists = glob(str(Path(ref_dir) / "*_starlist.txt"))
    if not starlists:
        return np.array([]), np.array([]), 0

    ids, xx, yy = np.loadtxt(starlists[0], unpack=True, delimiter=",")
    positions = tuple(zip(xx, yy))
    apertures = CircularAperture(positions, r=aperture_rad)
    rawflux = aperture_photometry(img, apertures)
    bkg_sum = img_median * (np.pi * aperture_rad ** 2)
    flx = rawflux["aperture_sum"] - bkg_sum
    flx_er = np.sqrt(np.abs(rawflux["aperture_sum"]))
    gd = np.where(flx > 0)[0]
    if len(gd) == 0:
        return np.array([]), np.array([]), 0

    flx = flx[gd]
    flx_er = flx_er[gd]
    x = np.array(xx[gd], dtype=np.float64)
    y = np.array(yy[gd], dtype=np.float64)
    mag = 25.0 - 2.5 * np.log10(flx)
    mag_er = (2.5 / np.log(10.0)) * (flx_er / flx)

    random.seed(random_seed)
    selected_x: list[int] = []
    selected_y: list[int] = []
    cnt = 0
    itr = 0
    while cnt < number_stars and itr < len(x):
        jj = random.randint(0, len(x) - 1)
        if (
            mag_er[jj] > 0
            and mag_er[jj] < 0.02
            and 50 < x[jj] < 1998
            and 50 < y[jj] < 1998
        ):
            dist = np.sqrt((x[jj] - x) ** 2 + (y[jj] - y) ** 2)
            idxs = np.where(dist < 3)[0]
            if len(idxs) == 1:
                selected_x.append(int(x[jj]))
                selected_y.append(int(y[jj]))
                cnt += 1
            elif len(idxs) > 0:
                dmag = mag[jj] - mag[idxs]
                cdmag = dmag[np.where(dmag != 0)]
                if len(np.where(cdmag > 0)[0]) == 0:
                    selected_x.append(int(x[jj]))
                    selected_y.append(int(y[jj]))
                    cnt += 1
        x = np.delete(x, jj)
        y = np.delete(y, jj)
        mag = np.delete(mag, jj)
        mag_er = np.delete(mag_er, jj)
        itr += 1

    return np.array(selected_x), np.array(selected_y), cnt
