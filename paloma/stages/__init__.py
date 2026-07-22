"""Concrete pipeline stages.

**Owned / implemented:** :class:`CleaningStage`.

**Shields only:** the other stages live in :mod:`paloma.stages.shields` and raise
:class:`NotImplementedError` if run.
"""

from .cleaning import CleaningStage
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
    "IngestionStage",
    "ValidationStage",
    "DetrendingStage",
    "NormalizationStage",
    "FeatureExtractionStage",
    "ClassificationStage",
]
