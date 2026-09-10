"""Core Paloma primitives for cleaning and image subtraction."""

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
from .chain import Chain, FunctionStage, Stage, as_stage, timed
from .types import (
    CleaningRequest,
    CleaningResult,
    SubtractionRequest,
    SubtractionResult,
)

__all__ = [
    "PipelineStage",
    "Stage",
    "Chain",
    "FunctionStage",
    "as_stage",
    "timed",
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
