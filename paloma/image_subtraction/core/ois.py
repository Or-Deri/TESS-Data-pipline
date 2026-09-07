"""Pure-Python Optimal Image Subtraction (OIS) engine — matches reference C layout."""

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
    """LU solve using flat column-major layout matching the reference C code."""
    c = c_flat.copy()
    low = np.zeros(q * q, dtype=np.float64)
    u = np.zeros(q * q, dtype=np.float64)

    for k in range(q):
        low[k + k * q] = 1.0
        for i in range(k + 1, q):
            low[k + i * q] = c[k + i * q] / c[k + k * q]
            for j in range(k + 1, q):
                c[j + i * q] -= low[k + i * q] * c[j + k * q]
        for j in range(k, q):
            u[j + k * q] = c[k + j * q]

    ycs = np.zeros(q, dtype=np.float64)
    rhs = d_vec.copy()
    for i in range(q - 1):
        for j in range(i + 1, q):
            ratio = low[j + i * q] / low[i + i * q]
            for count in range(i, q):
                idx = count + j * q
                src = count + i * count
                if src < low.size:
                    low[idx] -= ratio * low[src]
            rhs[j] -= ratio * rhs[i]

    ycs[q - 1] = rhs[q - 1] / low[(q - 1) + q * (q - 1)]
    for i in range(q - 2, -1, -1):
        temp = rhs[i]
        for j in range(i + 1, q):
            temp -= low[j + i * q] * ycs[j]
        ycs[i] = temp / low[i + i * q]

    xcs = np.zeros(q, dtype=np.float64)
    u_work = u.copy()
    y_work = ycs.copy()
    for i in range(q - 1):
        for j in range(i + 1, q):
            ratio = u_work[j + i * q] / u_work[i + i * q]
            for count in range(i, q):
                idx = count + j * q
                src = count + i * count
                if src < u_work.size:
                    u_work[idx] -= ratio * low[src]
            y_work[j] -= ratio * y_work[i]

    xcs[q - 1] = y_work[q - 1] / u_work[(q - 1) + q * (q - 1)]
    for i in range(q - 2, -1, -1):
        temp = y_work[i]
        for j in range(i + 1, q):
            temp -= u_work[j + i * q] * xcs[j]
        xcs[i] = temp / u_work[i + i * q]
    return xcs


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
