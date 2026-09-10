"""TESS Scattered-Light Removal via Spatio-Temporal Patch Recurrence.

- ``core`` — numeric primitives
- ``io`` — FITS load/save and layout
- ``workflow`` — concrete dehazing stages (uses ``paloma.core.chain``)
- ``runner`` — orchestration entry point (``dehaze``) + fluent facade
- ``evaluation`` — synthetic simulation / validation
"""

__version__ = "0.1.0"

from .config import DehazeConfig
from .runner import DehazePipeline, DehazeResult, dehaze
from .workflow import (
    Chain,
    FunctionStage,
    Stage,
    WorkflowContext,
    as_stage,
    build_chain,
)

__all__ = [
    "DehazeConfig",
    "DehazeResult",
    "dehaze",
    "DehazePipeline",
    "build_chain",
    "Chain",
    "Stage",
    "FunctionStage",
    "WorkflowContext",
    "as_stage",
    "__version__",
]
