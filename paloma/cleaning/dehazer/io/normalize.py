"""Linear [0, 1] normalization and its inverse.

See ``docs/workflow/02-load-normalize.md`` and ``06-recover-save.md``.
"""

import numpy as np


def normalize(frame, vmin, vmax):
    """Scale ``frame`` into [0, 1] using the given bounds (zeros if degenerate)."""
    rng = vmax - vmin
    if rng <= 0:
        return np.zeros_like(frame)
    return (frame - vmin) / rng


def denormalize(frame, vmin, vmax):
    """Invert :func:`normalize` back to the original physical scale."""
    return frame * (vmax - vmin) + vmin
