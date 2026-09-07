"""Source detection and cross-matching on residual images."""

from __future__ import annotations

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from photutils.detection import DAOStarFinder


def find_sources(
    img: np.ndarray,
    *,
    inverse: bool = False,
    edge_cutoff: int = 3,
    sigma: float = 3.0,
    maxiters: int = 5,
    fwhm: float = 1.5,
    threshold: float = 5.0,
    height: int = 2048,
    width: int = 2048,
) -> list[tuple[float, float]]:
    mean, median, std = sigma_clipped_stats(img, sigma=sigma, maxiters=maxiters)
    daofind = DAOStarFinder(fwhm=fwhm, threshold=threshold * std)
    sources = daofind(img - median)
    if sources is None:
        pixel_coord: list[tuple[float, float]] = []
    else:
        pixel_coord = list(zip(sources["xcentroid"], sources["ycentroid"]))

    inv_pixel_coord: list[tuple[float, float]] = []
    if inverse:
        inv_sources = daofind(-(img - median))
        if inv_sources is not None:
            inv_pixel_coord = [
                (x, y)
                for x, y in zip(inv_sources["xcentroid"], inv_sources["ycentroid"])
                if (x, y) not in pixel_coord
            ]

    positions: list[tuple[float, float]] = []
    for x, y in pixel_coord + inv_pixel_coord:
        if (
            x > edge_cutoff
            and y > edge_cutoff
            and x < (width - edge_cutoff)
            and y < (height - edge_cutoff)
        ):
            positions.append((float(x), float(y)))
    positions.sort()
    return positions


def filter_source_list(sources_list: list[list], threshold: float) -> list[list]:
    counts = [len(s) for s in sources_list]
    std_dev = np.std(counts)
    mean = np.mean(counts)
    return [s for s, n in zip(sources_list, counts) if n <= threshold * std_dev + mean]


def cross_match(ref_list: list, match_list: np.ndarray, search_radius: float) -> list:
    length_ref = len(ref_list)
    lower = 0
    for item in match_list:
        distance = search_radius + 1
        while lower < length_ref and ref_list[lower][0] < item[0] - search_radius:
            lower += 1
        upper = lower
        while upper < length_ref and ref_list[upper][0] < item[0] + search_radius:
            distance = np.hypot(ref_list[upper][0] - item[0], ref_list[upper][1] - item[1])
            if distance <= search_radius:
                ref_list[upper][2] += 1
                break
            if upper < length_ref - 1:
                upper += 1
            else:
                break
        if distance >= search_radius:
            insert_idx = lower
            while insert_idx < length_ref and ref_list[insert_idx][0] < item[0]:
                if insert_idx < length_ref - 1:
                    insert_idx += 1
                else:
                    break
            ref_list.insert(insert_idx, [float(item[0]), float(item[1]), 1])
            length_ref += 1
    return ref_list


def pixel_to_sky(pixel_sources: list, wcs: WCS) -> list[SkyCoord]:
    return [
        SkyCoord.from_pixel(coord[0], coord[1], wcs=wcs, mode="all")
        for coord in pixel_sources
    ]


def make_star_list(
    positions: list,
    ref_img: np.ndarray,
    aperture_rad: int,
    out_dir: str,
    ref_name: str,
) -> None:
    from pathlib import Path

    import scipy.stats
    from photutils.aperture import CircularAperture, aperture_photometry

    apertures = CircularAperture(positions, r=aperture_rad)
    phot_table = aperture_photometry(ref_img, apertures, method="exact")
    cimg, _, _ = scipy.stats.sigmaclip(ref_img, low=2.5, high=2.5)
    bkg_mean = np.median(cimg)
    flx = phot_table["aperture_sum"] - (bkg_mean * (np.pi * aperture_rad ** 2))
    x_pix = [p[0] for p in positions]
    y_pix = [p[1] for p in positions]
    gd = np.where(flx > 0)[0]
    if len(gd) == 0:
        return

    flx = flx[gd]
    x_pix = np.array(x_pix)[gd]
    y_pix = np.array(y_pix)[gd]
    ticid = range(len(x_pix))
    prefix = Path(out_dir) / Path(ref_name).stem
    with open(f"{prefix}.flux", "w", encoding="utf-8") as out:
        for i in range(len(x_pix)):
            if 0 < x_pix[i] < 2048 and 0 < y_pix[i] < 2048:
                out.write(f"{ticid[i]},{x_pix[i]},{y_pix[i]},{flx[i]}\n")
    with open(f"{prefix}_starlist.txt", "w", encoding="utf-8") as out:
        for i in range(len(x_pix)):
            if 0 < x_pix[i] < 2048 and 0 < y_pix[i] < 2048:
                out.write(f"{ticid[i]},{x_pix[i]},{y_pix[i]}\n")
