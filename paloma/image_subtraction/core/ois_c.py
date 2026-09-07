"""Optional C OIS backend (reference parity)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
from astropy.io import fits


def run_c_subtraction(
    reference: np.ndarray,
    science: np.ndarray,
    star_x: np.ndarray,
    star_y: np.ndarray,
    *,
    stamp: int,
    kernel: int,
    order: int,
    code_dir: str,
) -> np.ndarray:
    """Run the compiled ``a.out`` OIS binary; return residual image."""
    os.makedirs(code_dir, exist_ok=True)
    c_bin = Path(code_dir) / "a.out"
    if not c_bin.is_file():
        repo_root = Path(__file__).resolve().parents[3]
        src = repo_root / "build" / "a.out"
        if src.is_file():
            shutil.copy2(src, c_bin)

    fits.PrimaryHDU(reference.astype(np.float32)).writeto(
        Path(code_dir) / "ref.fits", overwrite=True
    )
    fits.PrimaryHDU(science.astype(np.float32)).writeto(
        Path(code_dir) / "img.fits", overwrite=True
    )
    with open(Path(code_dir) / "ref.txt", "w", encoding="utf-8") as fp:
        fp.write("ref.fits\n")
    with open(Path(code_dir) / "img.txt", "w", encoding="utf-8") as fp:
        fp.write("img.fits\n")
    with open(Path(code_dir) / "parms.txt", "w", encoding="utf-8") as fp:
        fp.write(f"{stamp} {kernel} {order} {len(star_x):4d}\n")
    with open(Path(code_dir) / "refstars.txt", "w", encoding="utf-8") as fp:
        for x, y in zip(star_x, star_y):
            fp.write(f"{int(x):4d} {int(y):4d}\n")

    result = subprocess.run(
        ["./a.out"],
        cwd=code_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    dimg = Path(code_dir) / "dimg.fits"
    if result.returncode != 0 or not dimg.is_file():
        raise RuntimeError(
            f"C OIS failed (code {result.returncode}): {result.stderr[:500]}"
        )
    data, _ = fits.getdata(dimg, header=True)
    return np.asarray(data, dtype=np.float64)
