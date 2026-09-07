"""Workflow chain engine and concrete subtraction stages."""

from .context import SubtractionWorkflowContext
from .engine import Chain, FunctionStage, Stage, as_stage, timed
from .stages import (
    BuildReference,
    DetectAndCrossMatch,
    ExtractLightCurves,
    OptimalSubtract,
    PreprocessFrames,
    build_chain,
)

__all__ = [
    "Stage",
    "Chain",
    "FunctionStage",
    "as_stage",
    "timed",
    "SubtractionWorkflowContext",
    "PreprocessFrames",
    "BuildReference",
    "OptimalSubtract",
    "DetectAndCrossMatch",
    "ExtractLightCurves",
    "build_chain",
]
