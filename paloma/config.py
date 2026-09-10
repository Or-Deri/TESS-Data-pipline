"""Pipeline stage configuration.

Selects which registered cleaner / subtractor runs and how each is parameterized.
:class:`PipelineConfig` loads the full Cleaning → Image Subtraction run from
``.env``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from paloma.env import resolve_path


@dataclass
class CleaningConfig:
    """Selects and configures the cleaning stage's algorithm.

    ``cleaner`` is the registered cleaner name (see
    :func:`paloma.core.cleaner.available_cleaners`); ``params`` are passed to
    that cleaner's constructor (e.g. ``{"strategy": "default", "num_frames": 5}``
    for the dehazer).
    """

    cleaner: str = "dehazer"
    params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls, *, load_dotenv: bool = True) -> "CleaningConfig":
        """Build from ``PALOMA_CLEANER`` + ``PALOMA_DEHAZE_*`` (when dehazer)."""
        from paloma.cleaning.dehazer.config import DehazeConfig
        from paloma.env import env_str, load_env

        if load_dotenv:
            load_env()
        cleaner = env_str("PALOMA_CLEANER", cls.cleaner) or cls.cleaner
        params: Dict[str, Any] = {}
        if cleaner == "dehazer":
            dehaze = DehazeConfig.from_env(load_dotenv=False)
            params = {
                **{k: v for k, v in dehaze.__dict__.items()},
                "strategy": env_str("PALOMA_DEHAZE_STRATEGY", "default") or "default",
            }
        return cls(cleaner=cleaner, params=params)


@dataclass
class ImageSubtractionConfig:
    """Selects and configures the image-subtraction stage (runs after cleaning)."""

    subtractor: str = "default"
    params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls, *, load_dotenv: bool = True) -> "ImageSubtractionConfig":
        """Build from ``PALOMA_SUBTRACTOR`` + ``PALOMA_SUBTRACTION_*``."""
        from paloma.env import env_str, load_env
        from paloma.image_subtraction.config import SubtractionConfig

        if load_dotenv:
            load_env()
        subtractor = env_str("PALOMA_SUBTRACTOR", cls.subtractor) or cls.subtractor
        params = SubtractionConfig.from_env(load_dotenv=False).__dict__.copy()
        return cls(subtractor=subtractor, params=params)


@dataclass
class PipelineConfig:
    """Full Cleaning → Image Subtraction run configuration."""

    cleaning: CleaningConfig = field(default_factory=CleaningConfig)
    subtraction: ImageSubtractionConfig = field(default_factory=ImageSubtractionConfig)
    input_dir: Optional[str] = None
    output_dir: Optional[str] = None
    cleaned_dir: Optional[str] = None
    subtracted_dir: Optional[str] = None

    def resolve_cleaned_dir(self, output_dir: Optional[str] = None) -> str:
        """Directory for cleaned FITS frames."""
        if self.cleaned_dir:
            return self.cleaned_dir
        root = output_dir or self.output_dir or "results"
        return str(Path(root) / "cleaned")

    def resolve_subtracted_dir(self, output_dir: Optional[str] = None) -> str:
        """Directory for subtraction outputs."""
        if self.subtracted_dir:
            return self.subtracted_dir
        root = output_dir or self.output_dir or "results"
        return str(Path(root) / "subtracted")

    @classmethod
    def from_env(cls, *, load_dotenv: bool = True) -> "PipelineConfig":
        """Load I/O paths + cleaning + subtraction from ``PALOMA_*``."""
        from paloma.env import env_str, load_env, paths_from_env

        if load_dotenv:
            load_env()
        paths = paths_from_env(load_dotenv=False)
        return cls(
            cleaning=CleaningConfig.from_env(load_dotenv=False),
            subtraction=ImageSubtractionConfig.from_env(load_dotenv=False),
            input_dir=paths.input_dir,
            output_dir=paths.output_dir,
            cleaned_dir=resolve_path(env_str("PALOMA_CLEANED_DIR")),
            subtracted_dir=resolve_path(env_str("PALOMA_SUBTRACTED_DIR")),
        )
