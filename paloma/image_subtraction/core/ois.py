"""Pure-Python Optimal Image Subtraction (OIS) engine.

The normal equations are accumulated in the same flat column-major layout as
the reference C implementation (``oisdifference.c``); the solve itself is
delegated to LAPACK via :func:`numpy.linalg.solve`.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import correlate


def _make_delta_kernel(nk: int, index: int, center: int) -> np.ndarray:
    kn = np.zeros(nk, dtype=np.float64)
    kn[index] = 1.0
    if index != center:
        kn[center] = -1.0
    return kn.reshape(int(np.sqrt(nk)), int(np.sqrt(nk)))


def _lu_solve(c_flat: np.ndarray, d_vec: np.ndarray, q: int) -> np.ndarray:
    """Solve the OIS normal equations ``C a = d`` for the kernel coefficients.

    ``c_flat`` is the column-major flattening of the symmetric ``q x q``
    matrix accumulated by :func:`optimal_subtract`, so element ``(row, col)``
    lives at ``c_flat[row + col * q]``.

    Falls back to a least-squares solution when the system is singular, which
    happens when the kernel stars do not constrain every basis term (too few
    stars, or stars that are collinear in the spatial polynomial).
    """
    matrix = np.asarray(c_flat, dtype=np.float64).reshape(q, q, order="F")
    rhs = np.asarray(d_vec, dtype=np.float64)
    try:
        return np.linalg.solve(matrix, rhs)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(matrix, rhs, rcond=None)[0]


def optimal_subtract(
    reference: np.ndarray,
    science: np.ndarray,
    star_x: np.ndarray,
    star_y: np.ndarray,
    *,
    stamp: int,
    kernel: int,
    order: int,
) -> np.ndarray:
    """Return residual ``science - convolved_reference``."""
    ref = np.asarray(reference, dtype=np.float64)
    sci = np.asarray(science, dtype=np.float64)
    naxes = ref.shape[0]
    w = kernel
    fwhm = stamp
    d = order
    l = 2 * w + 1
    nk = l * l
    stax = 2 * fwhm + 1
    deg = int(0.5 * (d + 1) * (d + 2))
    q = nk * deg
    center = (nk - 1) // 2
    p = len(star_x)

    ref_flat = ref.ravel()
    sci_flat = sci.ravel()
    xc = star_x.astype(np.int64)
    yc = star_y.astype(np.int64)

    c = np.zeros(q * q, dtype=np.float64)
    d_vec = np.zeros(q, dtype=np.float64)

    qrs = 0
    for q_idx in range(nk):
        kq2d = _make_delta_kernel(nk, q_idx, center)
        for r in range(d + 1):
            for s_idx in range(d - r + 1):
                for n_idx in range(nk):
                    kn2d = _make_delta_kernel(nk, n_idx, center)
                    ml = 0
                    for m in range(d + 1):
                        for l_idx in range(d - m + 1):
                            d_vec[qrs] = 0.0
                            for k in range(p):
                                xcent = xc[k]
                                ycent = yc[k]
                                rs = ref[ycent - fwhm : ycent + fwhm + 1, xcent - fwhm : xcent + fwhm + 1]
                                ss = sci[ycent - fwhm : ycent + fwhm + 1, xcent - fwhm : xcent + fwhm + 1]
                                crkn = correlate(rs, kn2d, mode="constant").ravel()
                                crkq = correlate(rs, kq2d, mode="constant").ravel()
                                mr = m + r
                                ls = l_idx + s_idx
                                row = n_idx * deg + ml
                                c[row + qrs * q] += np.sum((xcent ** mr) * (ycent ** ls) * crkn * crkq)
                                d_vec[qrs] += np.sum((xcent ** r) * (ycent ** s_idx) * ss.ravel() * crkq)
                            ml += 1
                qrs += 1

    a = _lu_solve(c, d_vec, q)

    con = np.zeros(ref_flat.size, dtype=np.float64)
    nml = 0
    for m in range(d + 1):
        for l_idx in range(d - m + 1):
            k_block = np.zeros(nk, dtype=np.float64)
            for i in range(nk):
                if i != center:
                    k_block[i] = a[deg * i + nml]
                    k_block[center] -= a[deg * i + nml]
                else:
                    k_block[center] += a[deg * i + nml]
            k2d = k_block.reshape(l, l)
            con += correlate(ref, k2d, mode="constant").ravel()
            nml += 1

    return (sci_flat - con).reshape(naxes, naxes)
