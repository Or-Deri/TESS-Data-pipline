"""Transmission map + scene recovery (haze-model inversion).

See ``README.md``.
"""

from .backend import get_array_module
from .guided_filter import guided_filter


def recover_transmission_map(image, a, radius=60, eps=0.001, t_min_clip=0.01):
    """Per-frame transmission map from the (smoothed) airlight scalar ``a``."""
    xp = get_array_module(image)
    a_safe = max(float(a), 1e-6)
    t_initial = 1.0 - image / a_safe
    t_initial = xp.clip(t_initial, t_min_clip, 0.9)
    t_refined = guided_filter(image, t_initial, radius, eps)
    return t_refined


def recover_image(image, a, t_map, t_min_clip=0.01):
    """Invert the haze model with scalar ``a`` and transmission ``t_map``."""
    xp = get_array_module(image)
    t_safe = xp.maximum(t_map, t_min_clip)
    recovered = (image - a) / t_safe + a
    return xp.clip(recovered, 0.0, 1.0)
