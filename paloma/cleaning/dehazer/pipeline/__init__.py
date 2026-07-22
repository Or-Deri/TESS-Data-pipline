"""Orchestration entry points: ``dehaze`` and the fluent facade."""

from .fluent import DehazePipeline
from .orchestration import (
    _get_fits_files,
    _iter_batches,
    _resolve_gpu,
    _write_output_location_marker,
    dehaze,
)

__all__ = [
    "dehaze",
    "DehazePipeline",
    "_get_fits_files",
    "_iter_batches",
    "_resolve_gpu",
    "_write_output_location_marker",
]
