"""Cleaning-stage configuration (owned).

Selects which registered :class:`~paloma.core.cleaner.Cleaner` runs and how it
is parameterized. Other pipeline stages are shields and have no config here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class CleaningConfig:
    """Selects and configures the cleaning stage's algorithm.

    ``cleaner`` is the registered cleaner name (see
    :func:`paloma.core.cleaner.available_cleaners`); ``params`` are passed to
    that cleaner's constructor (e.g. ``{"strategy": "default", "num_frames": 5}``
    for the dehazer).
    """

    cleaner: str = "dehazer"
    params: Dict[str, Any] = field(default_factory=dict)
