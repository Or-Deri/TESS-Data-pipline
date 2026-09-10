"""Preprocessing: quality filter, cutout, WCS alignment.

Accepts both raw TESS FFIs (science HDU 1 + WCS) and cleaned PrimaryHDU
frames from the dehazer (extension 0, often no WCS) so Cleaning → Subtraction
chains without a manual config swap.
"""

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
from paloma.core.log import info


def get_file_names(directory: str, pattern: str = "*.fits") -> list[str]:
    files = glob(os.path.join(directory, pattern))
    files.sort()
    return files


def remove_processed_files(file_list: list[str], out_dir: str, in_dir: str) -> list[str]:
    finished = get_file_names(out_dir, "*.fits")
    finished_in = {os.path.join(in_dir, os.path.basename(f)) for f in finished}
    return [f for f in file_list if f not in finished_in]


def science_hdu_index(hdul: fits.HDUList, preferred: int) -> int:
    """Return a 2-D image HDU index, preferring ``preferred`` when valid."""
    if 0 <= preferred < len(hdul):
        data = hdul[preferred].data
        if data is not None and getattr(data, "ndim", 0) == 2:
            return preferred
    for i, hdu in enumerate(hdul):
        data = hdu.data
        if data is not None and getattr(data, "ndim", 0) == 2:
            return i
    raise OSError("no 2-D image HDU")


def _has_wcs(header: fits.Header) -> bool:
    return "CTYPE1" in header and "CTYPE2" in header


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
                idx = science_hdu_index(hdul, cfg.fits_extension)
                data = hdul[idx].data
                head = hdul[idx].header
            if data is None:
                raise OSError("empty HDU")
            header_lengths.append(len(head))
        except (OSError, TypeError, IndexError, ValueError):
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
    # hcongrid requires NAXIS* to match the array; never force cutout_size here
    # (cleaned frames may already be cropped to a different geometry).
    head["NAXIS1"] = int(img.shape[1])
    head["NAXIS2"] = int(img.shape[0])
    if "CRPIX1" not in head:
        head["CRPIX1"] = cfg.crpix1
    img = hcongrid(img, head, ref_head)
    for key in ("CTYPE1", "CTYPE2", "CRVAL1", "CRVAL2", "CRPIX1", "CRPIX2",
                "CD1_1", "CD1_2", "CD2_1", "CD2_2"):
        if key in ref_head:
            head[key] = ref_head[key]
    head["align"] = "yes"
    head["bksub"] = "yes"
    return img, head


def _cutout_fits(img: np.ndarray, head: fits.Header, cfg: SubtractionConfig) -> tuple[np.ndarray, fits.Header]:
    """Cut out the configured window when geometry + WCS allow it."""
    head = head.copy()
    target_w, target_h = int(cfg.cutout_size[0]), int(cfg.cutout_size[1])

    # Already at (or below) target size — e.g. dehazer-cropped PrimaryHDU frames.
    if img.shape[1] <= target_w and img.shape[0] <= target_h:
        head["NAXIS1"] = int(img.shape[1])
        head["NAXIS2"] = int(img.shape[0])
        return img, head

    if not _has_wcs(head):
        head["NAXIS1"] = int(img.shape[1])
        head["NAXIS2"] = int(img.shape[0])
        return img, head

    try:
        cut = Cutout2D(img, cfg.cutout_center, cfg.cutout_size, wcs=WCS(head))
        data = cut.data
    except Exception:
        data = img

    head["NAXIS1"] = int(data.shape[1])
    head["NAXIS2"] = int(data.shape[0])
    if data.shape == (target_h, target_w):
        head["CRPIX1"] = cfg.crpix1
    return data, head


def preprocess_images(
    in_dir: str,
    out_dir: str,
    cfg: SubtractionConfig,
    files: list[str] | None = None,
) -> tuple[list[str], bool]:
    """Preprocess FFIs (raw or cleaned); return (preprocessed paths, did_work)."""
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
        idx = science_hdu_index(hdul, cfg.fits_extension)
        ref_img = hdul[idx].data
        ref_head = hdul[idx].header.copy()
    ref_img, ref_head = _cutout_fits(ref_img, ref_head, cfg)
    ref_head["NAXIS1"] = int(ref_img.shape[1])
    ref_head["NAXIS2"] = int(ref_img.shape[0])

    info(f"Preprocessing {len(pending)} frames ...")
    outputs = get_file_names(out_dir, "*.fits")
    for path in pending:
        with fits.open(path) as hdul:
            idx = science_hdu_index(hdul, cfg.fits_extension)
            img = hdul[idx].data
            head = hdul[idx].header.copy()
        img, head = _cutout_fits(img, head, cfg)
        head["NAXIS1"] = int(img.shape[1])
        head["NAXIS2"] = int(img.shape[0])
        if _has_wcs(head) and _has_wcs(ref_head):
            try:
                img, head = align_image(ref_head, img, head, cfg)
            except Exception:
                head["align"] = "skip"
                head["bksub"] = "yes"
        else:
            head["align"] = "skip"
            head["bksub"] = "yes"
        out_path = Path(out_dir) / Path(path).name
        fits.PrimaryHDU(img, header=head).writeto(out_path, overwrite=True)
        outputs.append(str(out_path))

    return sorted(set(outputs)), True
