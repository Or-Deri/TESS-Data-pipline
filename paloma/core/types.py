"""Shared domain types: cleaning contract (real) + shields for other stages.

**Owned / real (cleaning):** :class:`CleaningRequest`, :class:`CleaningResult`.

**Shields only:** :class:`LightCurve`, :class:`ProcessedLightCurve`,
:class:`FeatureVector`, :class:`ClassificationResult` — empty shells so other
stage owners can plug in later without inventing types ad hoc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence


# --- Cleaning (owned / real) -------------------------------------------------


@dataclass
class CleaningRequest:
    """Input to the cleaning stage: *what* data to clean and *where* to put it.

    ``input_dir`` holds the time-ordered ``*.fits`` FFI frames to clean and
    ``output_dir`` receives the cleaned frames. ``params`` carries optional
    per-run overrides for the active cleaner. *Which* cleaner runs is chosen by
    :class:`~paloma.config.CleaningConfig`, not by the request.
    """

    input_dir: str
    output_dir: str
    params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CleaningResult:
    """Output of the cleaning stage: the cleaned FFI frames on disk."""

    input_dir: str
    output_dir: str
    outputs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def num_outputs(self) -> int:
        return len(self.outputs)


# --- Shields for non-cleaning stages ----------------------------------------


@dataclass
class LightCurve:
    """Shield: a star's brightness over time."""

    time: Sequence[float] = ()
    flux: Sequence[float] = ()
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedLightCurve:
    """Shield: cleaned / detrended / normalized light curve."""

    time: Sequence[float] = ()
    flux: Sequence[float] = ()
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeatureVector:
    """Shield: numeric features for classification."""

    features: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClassificationResult:
    """Shield: final label for a light curve."""

    label: str = "unknown"  # "transit" | "EB" | "dwarf_star" | "unknown"
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
