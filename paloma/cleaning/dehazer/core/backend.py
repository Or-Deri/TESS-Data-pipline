"""Compute backend: GPU detection and GPU-agnostic array helpers.

Every function here works on both NumPy and CuPy arrays. When CuPy is not
installed (the common case) everything degrades to pure NumPy/SciPy on the CPU,
which is the canonical reference path (``docs/workflow/07-ops.md``).
"""

import shutil
import subprocess

import numpy as np
from scipy.ndimage import gaussian_filter1d

try:  # optional GPU backend
    import cupy as cp  # type: ignore
    from cupyx.scipy.ndimage import gaussian_filter1d as cp_gaussian_filter1d  # type: ignore

    _HAS_CUPY = True
except Exception:  # pragma: no cover - CuPy is optional
    cp = None
    cp_gaussian_filter1d = None
    _HAS_CUPY = False


def get_array_module(arr):
    """Return ``cupy`` if ``arr`` lives on the GPU, else ``numpy``."""
    if _HAS_CUPY and isinstance(arr, cp.ndarray):
        return cp
    return np


def to_gpu(arr):
    """Move an array to the GPU (no-op when CuPy is unavailable)."""
    if _HAS_CUPY:
        return cp.asarray(arr)
    return arr


def to_cpu(arr):
    """Return a host NumPy array regardless of the source device."""
    if _HAS_CUPY and isinstance(arr, cp.ndarray):
        return cp.asnumpy(arr)
    return np.asarray(arr)


def sliding_window_view(image, patch_size):
    """Overlapping (stride-1) window view of shape ``(H-p+1, W-p+1, p, p)``.

    Uses ``as_strided`` on the active array module. Falls back to
    ``skimage.util.view_as_windows`` if stride tricks are unavailable.
    """
    xp = get_array_module(image)
    p = patch_size
    h, w = image.shape
    shape = (h - p + 1, w - p + 1, p, p)
    try:
        strides = image.strides + image.strides
        return xp.lib.stride_tricks.as_strided(image, shape=shape, strides=strides)
    except Exception:  # pragma: no cover - defensive fallback
        from skimage.util import view_as_windows

        return view_as_windows(to_cpu(image), (p, p))


def find_nearest_neighbors(descriptors, chunk_size=4096):
    """Exact brute-force Euclidean nearest neighbour for each descriptor.

    Returns ``(nn_idx, nn_dist)``. Self-matches are excluded by setting the
    diagonal distance to ``+inf``. Ties resolve via ``argmin`` (first minimum),
    matching ``docs/workflow/03-estimate-airlight.md``.
    """
    xp = get_array_module(descriptors)
    n = descriptors.shape[0]
    sq_norms = xp.sum(descriptors ** 2, axis=1)
    nn_idx = xp.empty(n, dtype=xp.int64)
    nn_dist = xp.empty(n, dtype=descriptors.dtype)
    for start in range(0, n, chunk_size):
        end = min(start + chunk_size, n)
        chunk = descriptors[start:end]
        dist = (
            sq_norms[start:end, None]
            + sq_norms[None, :]
            - 2.0 * (chunk @ descriptors.T)
        )
        dist = xp.maximum(dist, 0)
        rows = xp.arange(end - start)
        dist[rows, rows + start] = xp.inf
        idx = xp.argmin(dist, axis=1)
        nn_idx[start:end] = idx
        nn_dist[start:end] = xp.sqrt(dist[rows, idx])
    return nn_idx, nn_dist


def gaussian_filter_temporal(cube, sigma):
    """1-D Gaussian smoothing along the temporal axis (axis 0) of a cube."""
    xp = get_array_module(cube)
    if _HAS_CUPY and xp is cp:
        return cp_gaussian_filter1d(cube, sigma=sigma, axis=0)
    return gaussian_filter1d(cube, sigma=sigma, axis=0)


def detect_gpu():
    """Return True if a usable CuPy device 0 is present."""
    if not _HAS_CUPY:
        return False
    try:  # pragma: no cover - requires hardware
        cp.cuda.Device(0).use()
        _ = cp.zeros(1)
        return True
    except Exception:
        return False


def is_gpu_free():
    """Require >=50% free VRAM on device 0 and <50% compute utilization."""
    if not _HAS_CUPY:
        return False
    try:  # pragma: no cover - requires hardware
        free, total = cp.cuda.Device(0).mem_info
        if total <= 0 or free / total < 0.5:
            return False
    except Exception:
        return False

    smi = shutil.which("nvidia-smi")
    if smi:
        try:  # pragma: no cover - requires hardware
            out = subprocess.check_output(
                [
                    smi,
                    "--query-gpu=utilization.gpu",
                    "--format=csv,noheader,nounits",
                    "--id=0",
                ],
                text=True,
            )
            if int(out.strip().splitlines()[0]) >= 50:
                return False
        except Exception:
            pass
    return True
