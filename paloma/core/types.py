"""Shared domain types for cleaning and image subtraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


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


@dataclass
class SubtractionRequest:
    """Input to the image-subtraction stage (typically cleaned FFIs from cleaning)."""

    input_dir: str
    output_dir: str
    params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_cleaning(
        cls,
        cleaning: "CleaningResult",
        output_dir: str,
        **params: Any,
    ) -> "SubtractionRequest":
        """Build a request chained from a :class:`CleaningResult`.

        Cleaned frames are PrimaryHDU (ext 0) and already accepted by cleaning,
        so DQUALITY filtering and the raw-FFI extension default are overridden
        unless the caller passes explicit values.
        """
        defaults = {
            "apply_data_quality_filter": False,
            "fits_extension": 0,
        }
        return cls(
            input_dir=cleaning.output_dir,
            output_dir=output_dir,
            params={**defaults, **params},
            metadata={"cleaning": cleaning.metadata, **cleaning.metadata},
        )


@dataclass
class SubtractionResult:
    """Output of image subtraction: residuals, source catalog, light curves."""

    input_dir: str
    output_dir: str
    outputs: List[str] = field(default_factory=list)
    sources_csv: str | None = None
    lightcurve_dir: str | None = None
    reference_fits: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def num_outputs(self) -> int:
        return len(self.outputs)
