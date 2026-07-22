"""Edge-preserving guided filter used to refine transmission maps.

See ``docs/workflow/05-transmission.md``.
"""

import numpy as np
from scipy.ndimage import uniform_filter

from .backend import get_array_module

try:  # optional GPU box filter
    from cupyx.scipy.ndimage import uniform_filter as cp_uniform_filter  # type: ignore
except Exception:  # pragma: no cover - CuPy optional
    cp_uniform_filter = None


def _box_filter(img, radius):
    """Mean (box) filter of window ``2*radius+1`` with reflect boundaries."""
    xp = get_array_module(img)
    size = 2 * radius + 1
    if xp is np or cp_uniform_filter is None:
        return uniform_filter(img, size=size, mode="reflect")
    return cp_uniform_filter(img, size=size, mode="reflect")


def guided_filter(guide, src, radius, eps):
    """Edge-preserving guided filter.

    CPU fast path uses ``cv2.ximgproc.guidedFilter`` in float32 when available;
    otherwise the pure array float64 box-filter formulation is used (also the
    GPU path). See ``docs/workflow/05-transmission.md``.
    """
    xp = get_array_module(guide)

    if xp is np:
        try:
            import cv2  # type: ignore

            if hasattr(cv2, "ximgproc"):
                g = np.asarray(guide, dtype=np.float32)
                s = np.asarray(src, dtype=np.float32)
                refined = cv2.ximgproc.guidedFilter(g, s, radius, eps)
                return np.asarray(refined, dtype=np.float64)
        except Exception:
            pass

    i = guide
    p = src
    mu_i = _box_filter(i, radius)
    mu_p = _box_filter(p, radius)
    cov_ip = _box_filter(i * p, radius) - mu_i * mu_p
    var_i = _box_filter(i * i, radius) - mu_i * mu_i
    a = cov_ip / (var_i + eps)
    b = mu_p - a * mu_i
    return _box_filter(a, radius) * i + _box_filter(b, radius)
