"""The chain engine and the concrete dehazing stages.

Import the engine (``Stage``, ``Chain``, ``WorkflowContext``) and the stages
(``build_chain`` and the individual step classes) from here.
"""

from paloma.core.chain import Chain, FunctionStage, Stage, as_stage, timed

from .context import WorkflowContext
from .stages import (
    EstimateAirlight,
    MoveCubeToDevice,
    RecoverAndSave,
    SmoothAirlight,
    Transmission,
    build_chain,
)

__all__ = [
    "Stage",
    "Chain",
    "FunctionStage",
    "as_stage",
    "timed",
    "WorkflowContext",
    "MoveCubeToDevice",
    "EstimateAirlight",
    "SmoothAirlight",
    "Transmission",
    "RecoverAndSave",
    "build_chain",
]
