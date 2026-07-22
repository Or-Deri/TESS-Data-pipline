"""Paloma — cleaning area + pipeline stage shields.

**Owned / real:** the cleaning area
(:class:`~paloma.core.cleaner.Cleaner`, :class:`~paloma.stages.cleaning.CleaningStage`,
:mod:`paloma.cleaning`).

**Shields only:** stub stages for the rest of the pipeline shape
(:mod:`paloma.stages.shields`) and empty domain-type shells for those stages.
"""

__version__ = "0.1.0"

from .config import CleaningConfig
from .core import (
    BaseCleaner,
    ClassificationResult,
    Cleaner,
    CleaningRequest,
    CleaningResult,
    FeatureVector,
    LightCurve,
    PipelineStage,
    ProcessedLightCurve,
    available_cleaners,
    create_cleaner,
    register_cleaner,
)

from . import cleaning  # noqa: E402  # registers built-in cleaners
from .cleaning import DehazerCleaner  # noqa: E402
from .stages import (  # noqa: E402
    ClassificationStage,
    CleaningStage,
    DetrendingStage,
    FeatureExtractionStage,
    IngestionStage,
    NormalizationStage,
    ValidationStage,
)

__all__ = [
    # Framework (needed by cleaner + shields)
    "PipelineStage",
    # Cleaning — owned / real
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
    # Shields — other stages / domain types
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
