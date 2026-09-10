"""Paloma — cleaning and image subtraction pipeline.

Two stages: :class:`~paloma.pipeline.CleaningStage` then
:class:`~paloma.pipeline.ImageSubtractionStage`.

Run both via :class:`~paloma.pipeline.Pipeline` / ``python -m paloma``.
"""

__version__ = "0.1.0"

from .config import CleaningConfig, ImageSubtractionConfig, PipelineConfig
from .env import IOPaths, load_env, paths_from_env
from .core import (
    BaseCleaner,
    BaseSubtractor,
    Cleaner,
    CleaningRequest,
    CleaningResult,
    PipelineStage,
    SubtractionRequest,
    SubtractionResult,
    Subtractor,
    available_cleaners,
    available_subtractors,
    create_cleaner,
    create_subtractor,
    register_cleaner,
    register_subtractor,
)

from . import cleaning  # noqa: E402  # registers built-in cleaners
from . import image_subtraction  # noqa: E402  # registers default subtractor
from .cleaning import DehazerCleaner  # noqa: E402
from .image_subtraction import DefaultSubtractor  # noqa: E402
from .pipeline import (  # noqa: E402
    CleaningStage,
    ImageSubtractionStage,
    Pipeline,
    PipelineResult,
)

__all__ = [
    "PipelineStage",
    "Pipeline",
    "PipelineConfig",
    "PipelineResult",
    # Cleaning
    "Cleaner",
    "BaseCleaner",
    "register_cleaner",
    "create_cleaner",
    "available_cleaners",
    "DehazerCleaner",
    "CleaningRequest",
    "CleaningResult",
    "CleaningStage",
    "CleaningConfig",
    # Image subtraction (after cleaning)
    "Subtractor",
    "BaseSubtractor",
    "register_subtractor",
    "create_subtractor",
    "available_subtractors",
    "DefaultSubtractor",
    "SubtractionRequest",
    "SubtractionResult",
    "ImageSubtractionStage",
    "ImageSubtractionConfig",
    "load_env",
    "paths_from_env",
    "IOPaths",
    "__version__",
]
