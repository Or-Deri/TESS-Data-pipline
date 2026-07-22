"""Transmission-map estimation (Step 3).

See ``docs/workflow/05-transmission.md``.
"""

from .backend import get_array_module
from .guided_filter import guided_filter


def recover_transmission_map(image, a, radius=60, eps=0.001, t_min_clip=0.01):
    """Per-frame transmission map from the (smoothed) airlight scalar ``a``."""
    xp = get_array_module(image)
    a_safe = max(float(a), 1e-6)
    t_initial = 1.0 - image / a_safe
    t_initial = xp.clip(t_initial, t_min_clip, 0.9)
    print(
        f"    Transmission (initial): "
        f"min={float(t_initial.min()):.4f}, max={float(t_initial.max()):.4f}, "
        f"mean={float(t_initial.mean()):.4f}"
    )
    t_refined = guided_filter(image, t_initial, radius, eps)
    print(
        f"    Transmission (refined): "
        f"min={float(t_refined.min()):.4f}, max={float(t_refined.max()):.4f}, "
        f"mean={float(t_refined.mean()):.4f}"
    )
    return t_refined
