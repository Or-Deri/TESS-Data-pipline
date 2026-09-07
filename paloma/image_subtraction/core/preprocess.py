"""Preprocessing: quality filter, cutout, WCS alignment."""

from __future__ import annotations

import os
from glob import glob
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.nddata.utils import Cutout2D
from astropy.wcs import WCS
from FITS_tools.hcongrid import hcongrid

from ..config import SubtractionConfig


def get_file_names(directory: str, pattern: str = "*.fits") -> list[str]:
    files = glob(os.path.join(directory, pattern))
    files.sort()
    return files


def remove_processed_files(file_list: list[str], out_dir: str, in_dir: str) -> list[str]:
    finished = get_file_names(out_dir, "*.fits")
    finished_in = {os.path.join(in_dir, os.path.basename(f)) for f in finished}
    return [f for f in file_list if f not in finished_in]


def file_filter(
    file_list: list[str],
    cfg: SubtractionConfig,
    *,
    check_header: bool = True,
    save_rejected: bool = True,
    out_path: str = "",
) -> list[str]:
    accepted, rejected, header_lengths = [], [], []
    for path in file_list:
        try:
            with fits.open(path) as hdul:
                data = hdul[cfg.fits_extension].data
                head = hdul[cfg.fits_extension].header
            if data is None:
                raise OSError("empty HDU")
            header_lengths.append(len(head))
        except (OSError, TypeError, IndexError):
            rejected.append(path)
            if save_rejected and out_path:
                with open(os.path.join(out_path, "rejectedFiles.txt"), "a+", encoding="utf-8") as fp:
                    fp.write(f"{path}: could not open\n")
            continue

        if check_header and len(head) != int(np.median(header_lengths)):
            rejected.append(path)
            if save_rejected and out_path:
                with open(os.path.join(out_path, "rejectedFiles.txt"), "a+", encoding="utf-8") as fp:
                    fp.write(f"{path}: header is different\n")
            continue

        if cfg.apply_data_quality_filter and "DQUALITY" in head:
            if (head["DQUALITY"] & cfg.data_quality_mask) != 0:
                rejected.append(path)
                if save_rejected and out_path:
                    with open(os.path.join(out_path, "rejectedFiles.txt"), "a+", encoding="utf-8") as fp:
                        fp.write(f"{path}: data quality flag\n")
                continue

        accepted.append(path)
    return accepted


def align_image(ref_head: fits.Header, img: np.ndarray, head: fits.Header, cfg: SubtractionConfig):
    head = head.copy()
    head["NAXIS1"] = cfg.cutout_size[0]
    head["NAXIS2"] = cfg.cutout_size[1]
    head["CRPIX1"] = cfg.crpix1
    img = hcongrid(img, head, ref_head)
    for key in ("CTYPE1", "CTYPE2", "CRVAL1", "CRVAL2", "CRPIX1", "CRPIX2",
                "CD1_1", "CD1_2", "CD2_1", "CD2_2"):
        if key in ref_head:
            head[key] = ref_head[key]
    head["align"] = "yes"
    head["bksub"] = "yes"
    return img, head


def preprocess_images(
    in_dir: str,
    out_dir: str,
    cfg: SubtractionConfig,
    files: list[str] | None = None,
) -> tuple[list[str], bool]:
    """Preprocess raw FFIs; return (preprocessed paths, did_work)."""
    os.makedirs(out_dir, exist_ok=True)
    raw_all = files or get_file_names(in_dir, "*.fits")
    if cfg.num_frames is not None:
        raw_all = raw_all[: cfg.num_frames]

    if not raw_all:
        return [], False

    pending = remove_processed_files(raw_all, out_dir, in_dir)
    pending = file_filter(pending, cfg, out_path=out_dir)
    if not pending:
        existing = get_file_names(out_dir, "*.fits")
        return existing, False

    with fits.open(pending[0]) as hdul:
        ref_img = hdul[cfg.fits_extension].data
        ref_head = hdul[cfg.fits_extension].header.copy()
    ref_head["CRPIX1"] = cfg.crpix1
    ref_head["NAXIS1"] = cfg.cutout_size[0]
    ref_head["NAXIS2"] = cfg.cutout_size[1]

    outputs = get_file_names(out_dir, "*.fits")
    for path in pending:
        with fits.open(path) as hdul:
            img = hdul[cfg.fits_extension].data
            head = hdul[cfg.fits_extension].header.copy()
        img = Cutout2D(img, cfg.cutout_center, cfg.cutout_size, wcs=WCS(head)).data
        head["NAXIS1"] = cfg.cutout_size[0]
        head["NAXIS2"] = cfg.cutout_size[1]
        head["CRPIX1"] = cfg.crpix1
        img, head = align_image(ref_head, img, head, cfg)
        out_path = Path(out_dir) / Path(path).name
        fits.PrimaryHDU(img, header=head).writeto(out_path, overwrite=True)
        outputs.append(str(out_path))

    return sorted(set(outputs)), True
