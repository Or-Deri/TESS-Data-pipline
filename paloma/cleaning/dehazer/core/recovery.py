"""Scene recovery: haze-model inversion (Step 4 numeric core).

See ``docs/workflow/06-recover-save.md``.
"""

from .backend import get_array_module


def recover_image(image, a, t_map, t_min_clip=0.01):
    """Invert the haze model with scalar ``a`` and transmission ``t_map``."""
    xp = get_array_module(image)
    t_safe = xp.maximum(t_map, t_min_clip)
    recovered = (image - a) / t_safe + a
    return xp.clip(recovered, 0.0, 1.0)
