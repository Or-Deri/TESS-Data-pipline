"""Core Paloma primitives used by cleaning and stage shields."""

from .cleaner import (
    BaseCleaner,
    Cleaner,
    available_cleaners,
    create_cleaner,
    register_cleaner,
)
from .stage import PipelineStage
from .types import (
    ClassificationResult,
    CleaningRequest,
    CleaningResult,
    FeatureVector,
    LightCurve,
    ProcessedLightCurve,
)

__all__ = [
    "PipelineStage",
    "LightCurve",
    "ProcessedLightCurve",
    "FeatureVector",
    "ClassificationResult",
    "CleaningRequest",
    "CleaningResult",
    "Cleaner",
    "BaseCleaner",
    "register_cleaner",
    "create_cleaner",
    "available_cleaners",
]
