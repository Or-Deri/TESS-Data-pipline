"""Core Paloma primitives used by cleaning and stage shields."""

from .cleaner import (
    BaseCleaner,
    Cleaner,
    available_cleaners,
    create_cleaner,
    register_cleaner,
)
from .subtractor import (
    BaseSubtractor,
    Subtractor,
    available_subtractors,
    create_subtractor,
    register_subtractor,
)
from .stage import PipelineStage
from .types import (
    ClassificationResult,
    CleaningRequest,
    CleaningResult,
    FeatureVector,
    LightCurve,
    ProcessedLightCurve,
    SubtractionRequest,
    SubtractionResult,
)

__all__ = [
    "PipelineStage",
    "LightCurve",
    "ProcessedLightCurve",
    "FeatureVector",
    "ClassificationResult",
    "CleaningRequest",
    "CleaningResult",
    "SubtractionRequest",
    "SubtractionResult",
    "Cleaner",
    "BaseCleaner",
    "register_cleaner",
    "create_cleaner",
    "available_cleaners",
    "Subtractor",
    "BaseSubtractor",
    "register_subtractor",
    "create_subtractor",
    "available_subtractors",
]
