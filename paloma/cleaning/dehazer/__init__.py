"""TESS Scattered-Light Removal via Spatio-Temporal Patch Recurrence.

Canonical implementation of the 3-D (spatio-temporal) blind-dehazing pipeline
described in ``docs/workflow``. The package is organized into subpackages by
concern:

- ``core``       — device-agnostic numeric primitives (backend, patches,
                   airlight, guided filter, transmission, recovery)
- ``io``         — FITS load/save, normalization, output-path layout
- ``workflow``   — the Stage/Chain engine and the concrete pipeline stages
- ``pipeline``   — orchestration (``dehaze``) + fluent facade
- ``strategies`` — pluggable Strategy layer for embedding in a larger pipeline
- ``evaluation`` — synthetic-data simulation and validation

The names below form the stable public API; import them straight from
``tess_dehazing``.
"""

__version__ = "0.1.0"

from .config import DehazeConfig
from .pipeline import DehazePipeline, dehaze
from .strategies import (
    BaseDehazer,
    DehazeResult,
    Dehazer,
    DehazingContext,
    DehazingStrategy,
    available_strategies,
    create_dehazer,
    register_strategy,
)
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
    # High-level strategy API (for embedding in a larger pipeline)
    "Dehazer",
    "BaseDehazer",
    "DehazingStrategy",
    "DehazingContext",
    "DehazeResult",
    "create_dehazer",
    "register_strategy",
    "available_strategies",
    # Direct entry points
    "dehaze",
    "DehazePipeline",
    # Chain engine
    "build_chain",
    "Chain",
    "Stage",
    "FunctionStage",
    "WorkflowContext",
    "as_stage",
    "__version__",
]
