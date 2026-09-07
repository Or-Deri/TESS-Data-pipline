"""Cleaning-stage configuration (owned).

Selects which registered :class:`~paloma.core.cleaner.Cleaner` runs and how it
is parameterized. Other pipeline stages are shields and have no config here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


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
