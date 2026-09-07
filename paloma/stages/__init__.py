"""Concrete pipeline stages.

**Owned / implemented:** :class:`CleaningStage`, :class:`ImageSubtractionStage`.

**Shields only:** other stages in :mod:`paloma.stages.shields`.
"""

from .cleaning import CleaningStage
from .image_subtraction import ImageSubtractionStage
from .shields import (
    ClassificationStage,
    DetrendingStage,
    FeatureExtractionStage,
    IngestionStage,
    NormalizationStage,
    ValidationStage,
)

__all__ = [
    "CleaningStage",
    "ImageSubtractionStage",
    "IngestionStage",
    "ValidationStage",
    "DetrendingStage",
    "NormalizationStage",
    "FeatureExtractionStage",
    "ClassificationStage",
]
