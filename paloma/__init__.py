"""Paloma — cleaning, image subtraction, + pipeline stage shields.

**Owned / real:** cleaning (:class:`~paloma.core.cleaner.Cleaner`,
:class:`~paloma.stages.cleaning.CleaningStage`) and image subtraction
(:class:`~paloma.core.subtractor.Subtractor`,
:class:`~paloma.stages.image_subtraction.ImageSubtractionStage`).

**Shields only:** stub stages for the rest of the pipeline shape.
"""

__version__ = "0.1.0"

from .config import CleaningConfig, ImageSubtractionConfig
from .env import IOPaths, load_env, paths_from_env
from .core import (
    BaseCleaner,
    BaseSubtractor,
    ClassificationResult,
    Cleaner,
    CleaningRequest,
    CleaningResult,
    FeatureVector,
    LightCurve,
    PipelineStage,
    ProcessedLightCurve,
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
from .stages import (  # noqa: E402
    ClassificationStage,
    CleaningStage,
    DetrendingStage,
    FeatureExtractionStage,
    ImageSubtractionStage,
    IngestionStage,
    NormalizationStage,
    ValidationStage,
)

__all__ = [
    # Framework
    "PipelineStage",
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
    # Shields
    "IngestionStage",
    "ValidationStage",
    "DetrendingStage",
    "NormalizationStage",
    "FeatureExtractionStage",
    "ClassificationStage",
    "LightCurve",
    "ProcessedLightCurve",
    "FeatureVector",
    "ClassificationResult",
    "__version__",
]
