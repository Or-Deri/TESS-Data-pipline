"""Optimal Image Subtraction (OIS) engine for TESS FFIs.

Runs as the pipeline stage *after* cleaning — not a :class:`~paloma.core.cleaner.Cleaner`.
"""

__version__ = "0.1.0"

from .config import SubtractionConfig
from .pipeline import DefaultSubtractor, subtract  # noqa: F401 — registers subtractor
from .workflow import SubtractionWorkflowContext, build_chain

__all__ = [
    "SubtractionConfig",
    "subtract",
    "DefaultSubtractor",
    "SubtractionWorkflowContext",
    "build_chain",
    "__version__",
]
