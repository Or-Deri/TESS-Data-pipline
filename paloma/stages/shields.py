"""Pipeline stage shields (stubs) for everything outside Cleaning.

Only :class:`~paloma.stages.cleaning.CleaningStage` is implemented. The stages
below keep the pipeline shape visible; each ``run`` raises
:class:`NotImplementedError` until its owner fills it in.
"""

from __future__ import annotations

from typing import Any, Optional

from ..core.stage import PipelineStage


class _ShieldStage(PipelineStage[Any, Any]):
    """Base for unimplemented stages — raises if called."""

    def run(self, data: Any) -> Optional[Any]:
        raise NotImplementedError(
            f"{type(self).__name__} is a pipeline shield only; "
            "not yet implemented (outside the cleaning ownership)."
        )


class IngestionStage(_ShieldStage):
    """Shield: raw FITS → LightCurve."""

    name = "ingestion"


class ValidationStage(_ShieldStage):
    """Shield: validate a LightCurve."""

    name = "validation"


class DetrendingStage(_ShieldStage):
    """Shield: remove slow trends from a light curve."""

    name = "detrending"


class NormalizationStage(_ShieldStage):
    """Shield: rescale flux → ProcessedLightCurve."""

    name = "normalization"


class FeatureExtractionStage(_ShieldStage):
    """Shield: light curve → FeatureVector."""

    name = "feature_extraction"


class ClassificationStage(_ShieldStage):
    """Shield: features → ClassificationResult."""

    name = "classification"


__all__ = [
    "IngestionStage",
    "ValidationStage",
    "DetrendingStage",
    "NormalizationStage",
    "FeatureExtractionStage",
    "ClassificationStage",
]
