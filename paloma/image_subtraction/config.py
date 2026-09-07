"""Configuration for the optimal image subtraction pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SubtractionConfig:
    """All tunable parameters for the OIS pipeline."""

    kernel: int = 2
    stamp: int = 3
    order: int = 0
    nr_stars: int = 500
    blknum: int = 50
    num_iterations: int = 2
    aperture_rad: int = 3
    threshold_source_detection: float = 50.0
    fwhm: float = 1.5
    edge_cutoff: int = 3
    match_radius: int = 3
    random_seed: int = 0
    data_quality_mask: int = 0b110010111101
    apply_data_quality_filter: bool = True
    cutout_center: tuple = (1068, 1024)
    cutout_size: tuple = (2048, 2048)
    crpix1: float = 1001.0
    fits_extension: int = 1
    num_frames: int | None = None
    source_filter_threshold: float = 1.5
    use_c_backend: bool = True
    code_dir: str | None = None

    @classmethod
    def from_env(cls, *, load_dotenv: bool = True) -> "SubtractionConfig":
        """Build config from ``PALOMA_SUBTRACTION_*`` environment variables."""
        from paloma.env import (
            env_bool,
            env_float,
            env_int,
            env_int_pair,
            env_str,
            load_env,
            resolve_path,
        )

        if load_dotenv:
            load_env()
        cfg = cls(
            kernel=env_int("PALOMA_SUBTRACTION_KERNEL", cls.kernel),
            stamp=env_int("PALOMA_SUBTRACTION_STAMP", cls.stamp),
            order=env_int("PALOMA_SUBTRACTION_ORDER", cls.order),
            nr_stars=env_int("PALOMA_SUBTRACTION_NR_STARS", cls.nr_stars),
            blknum=env_int("PALOMA_SUBTRACTION_BLKNUM", cls.blknum),
            num_iterations=env_int(
                "PALOMA_SUBTRACTION_NUM_ITERATIONS", cls.num_iterations
            ),
            aperture_rad=env_int(
                "PALOMA_SUBTRACTION_APERTURE_RAD", cls.aperture_rad
            ),
            threshold_source_detection=env_float(
                "PALOMA_SUBTRACTION_THRESHOLD_SOURCE_DETECTION",
                cls.threshold_source_detection,
            ),
            fwhm=env_float("PALOMA_SUBTRACTION_FWHM", cls.fwhm),
            edge_cutoff=env_int(
                "PALOMA_SUBTRACTION_EDGE_CUTOFF", cls.edge_cutoff
            ),
            match_radius=env_int(
                "PALOMA_SUBTRACTION_MATCH_RADIUS", cls.match_radius
            ),
            random_seed=env_int(
                "PALOMA_SUBTRACTION_RANDOM_SEED", cls.random_seed
            ),
            data_quality_mask=env_int(
                "PALOMA_SUBTRACTION_DATA_QUALITY_MASK", cls.data_quality_mask
            ),
            apply_data_quality_filter=env_bool(
                "PALOMA_SUBTRACTION_APPLY_DATA_QUALITY_FILTER",
                cls.apply_data_quality_filter,
            ),
            cutout_center=env_int_pair(
                "PALOMA_SUBTRACTION_CUTOUT_CENTER", cls.cutout_center
            ),
            cutout_size=env_int_pair(
                "PALOMA_SUBTRACTION_CUTOUT_SIZE", cls.cutout_size
            ),
            crpix1=env_float("PALOMA_SUBTRACTION_CRPIX1", cls.crpix1),
            fits_extension=env_int(
                "PALOMA_SUBTRACTION_FITS_EXTENSION", cls.fits_extension
            ),
            num_frames=env_int("PALOMA_SUBTRACTION_NUM_FRAMES", None),
            source_filter_threshold=env_float(
                "PALOMA_SUBTRACTION_SOURCE_FILTER_THRESHOLD",
                cls.source_filter_threshold,
            ),
            use_c_backend=env_bool(
                "PALOMA_SUBTRACTION_USE_C_BACKEND", cls.use_c_backend
            ),
            code_dir=env_str("PALOMA_SUBTRACTION_CODE_DIR", cls.code_dir),
        )
        if cfg.code_dir:
            cfg.code_dir = resolve_path(cfg.code_dir)
        return cfg
