"""Configuration for the dehazing pipeline.

The defaults here are the canonical reproduction constants documented in
``README.md``. Changing any of them changes numeric output.
"""

from __future__ import annotations

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

    @classmethod
    def from_env(cls, *, load_dotenv: bool = True) -> "DehazeConfig":
        """Build config from ``PALOMA_DEHAZE_*`` environment variables."""
        from paloma.env import (
            env_bool,
            env_float,
            env_int,
            load_env,
        )

        if load_dotenv:
            load_env()
        return cls(
            patch_size=env_int("PALOMA_DEHAZE_PATCH_SIZE", cls.patch_size),
            variance_threshold=env_float(
                "PALOMA_DEHAZE_VARIANCE_THRESHOLD", cls.variance_threshold
            ),
            nn_dist_threshold=env_float(
                "PALOMA_DEHAZE_NN_DIST_THRESHOLD", cls.nn_dist_threshold
            ),
            sigma_temporal=env_float(
                "PALOMA_DEHAZE_SIGMA_TEMPORAL", cls.sigma_temporal
            ),
            t_min_clip=env_float("PALOMA_DEHAZE_T_MIN_CLIP", cls.t_min_clip),
            guided_filter_radius=env_int(
                "PALOMA_DEHAZE_GUIDED_FILTER_RADIUS", cls.guided_filter_radius
            ),
            guided_filter_eps=env_float(
                "PALOMA_DEHAZE_GUIDED_FILTER_EPS", cls.guided_filter_eps
            ),
            num_frames=env_int("PALOMA_DEHAZE_NUM_FRAMES", cls.num_frames),
            batch_size=env_int("PALOMA_DEHAZE_BATCH_SIZE", None),
            use_gpu=env_bool("PALOMA_DEHAZE_USE_GPU", cls.use_gpu),
            crop_bottom=env_int("PALOMA_DEHAZE_CROP_BOTTOM", cls.crop_bottom),
            crop_sides=env_int("PALOMA_DEHAZE_CROP_SIDES", cls.crop_sides),
            max_patches=env_int("PALOMA_DEHAZE_MAX_PATCHES", None),
            num_iterations=env_int(
                "PALOMA_DEHAZE_NUM_ITERATIONS", cls.num_iterations
            ),
            fits_extension=env_int(
                "PALOMA_DEHAZE_FITS_EXTENSION", cls.fits_extension
            ),
        )
