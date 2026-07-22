"""Configuration for the dehazing pipeline.

The defaults here are the canonical reproduction constants documented in
``docs/workflow/01-setup.md``. Changing any of them changes numeric output.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DehazeConfig:
    """All tunable parameters for the 3-D dehazing pipeline."""

    patch_size: int = 9
    variance_threshold: float = 5e-5
    nn_dist_threshold: float = 0.3
    sigma_temporal: float = 1.5
    t_min_clip: float = 0.01
    guided_filter_radius: int = 60
    guided_filter_eps: float = 0.001
    num_frames: int = 10
    batch_size: Optional[int] = None
    use_gpu: bool = False
    crop_bottom: int = 30
    crop_sides: int = 44
    max_patches: Optional[int] = None
    num_iterations: int = 10
    fits_extension: int = 1
