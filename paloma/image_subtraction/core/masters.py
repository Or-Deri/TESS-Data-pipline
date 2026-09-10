"""Master frame construction."""

from __future__ import annotations

import os

import numpy as np
from astropy.io import fits

from ..config import SubtractionConfig
from .preprocess import _has_wcs, align_image, get_file_names


def _combine_aligned(rhead: fits.Header, combined: np.ndarray, cfg: SubtractionConfig):
    """Align ``combined`` onto ``rhead`` when WCS exists; otherwise pass through."""
    if _has_wcs(rhead):
        return align_image(rhead, combined, rhead.copy(), cfg)
    head = rhead.copy()
    head["NAXIS1"] = combined.shape[1]
    head["NAXIS2"] = combined.shape[0]
    head["align"] = "skip"
    head["bksub"] = "yes"
    return combined, head


def make_master(file_names: list[str], in_dir: str, out_dir: str, cfg: SubtractionConfig) -> list[str]:
    """Build block median master frames."""
    os.makedirs(out_dir, exist_ok=True)
    blknum = cfg.blknum
    file_names = file_names or get_file_names(in_dir, "*.fits")
    if not file_names:
        return []

    outputs: list[str] = []
    cnt = 0
    kk = 0
    _, rhead = fits.getdata(file_names[0], header=True)
    nx = fits.getval(file_names[0], "NAXIS2")
    ny = fits.getval(file_names[0], "NAXIS1")
    all_data = np.ndarray(shape=(blknum, nx, ny))
    expt = np.zeros(blknum)

    for ii, fname in enumerate(file_names):
        path = os.path.join(in_dir, os.path.basename(fname)) if not os.path.isabs(fname) else fname
        if not os.path.isfile(path):
            path = fname
        all_data[cnt] = fits.getdata(path)
        expt[cnt] = fits.getval(path, "EXPOSURE")
        cnt += 1

        if (ii == len(file_names) - 1) or ((ii + 1) % blknum == 0):
            combined = np.median(all_data[:cnt], axis=0)
            img, head = _combine_aligned(rhead, combined, cfg)
            hdu = fits.PrimaryHDU(img, header=head)
            hdu.header["NUMCOB"] = cnt
            hdu.header["EXPOSURE"] = float(np.median(expt[:cnt]))
            outname = f"master_{kk:03d}.fits"
            out_path = os.path.join(out_dir, outname)
            hdu.writeto(out_path, overwrite=True)
            outputs.append(out_path)
            kk += 1
            cnt = 0
            all_data = np.ndarray(shape=(blknum, nx, ny))
            expt = np.zeros(blknum)

    return outputs


def build_final_master(file_names: list[str], in_dir: str, out_dir: str, cfg: SubtractionConfig) -> str:
    """Median-combine block masters into the final reference."""
    os.makedirs(out_dir, exist_ok=True)
    if not file_names:
        file_names = [os.path.basename(p) for p in get_file_names(in_dir, "*.fits")]

    nx = fits.getval(os.path.join(in_dir, file_names[0]), "NAXIS2")
    ny = fits.getval(os.path.join(in_dir, file_names[0]), "NAXIS1")
    all_data = np.ndarray(shape=(len(file_names), nx, ny))
    expt = np.zeros(len(file_names))
    num = np.zeros(len(file_names))

    _, rhead = fits.getdata(os.path.join(in_dir, file_names[0]), header=True)
    for ii, fname in enumerate(file_names):
        path = os.path.join(in_dir, fname)
        all_data[ii] = fits.getdata(path)
        expt[ii] = fits.getval(path, "EXPOSURE")
        num[ii] = fits.getval(path, "NUMCOB")

    combined = np.median(all_data, axis=0)
    img, head = _combine_aligned(rhead, combined, cfg)
    hdu = fits.PrimaryHDU(img, header=head)
    hdu.header["NUMCOB"] = float(np.sum(num))
    hdu.header["EXPOSURE"] = float(np.median(expt))
    out_path = os.path.join(out_dir, "master_final.fits")
    hdu.writeto(out_path, overwrite=True)
    return out_path
