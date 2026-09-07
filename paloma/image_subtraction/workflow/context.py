"""Mutable state threaded through subtraction workflow stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from ..config import SubtractionConfig
from ..io.layout import RunLayout


@dataclass
class SubtractionWorkflowContext:
    cfg: SubtractionConfig
    input_dir: str
    output_dir: str
    layout: RunLayout
    label: str = ""

    raw_files: List[str] = field(default_factory=list)
    preprocessed_files: List[str] = field(default_factory=list)
    master_files: List[str] = field(default_factory=list)
    reference_fits: Optional[str] = None
    residual_files: List[str] = field(default_factory=list)
    source_list: List[list] = field(default_factory=list)
    sources_csv: Optional[str] = None
    lightcurve_files: List[str] = field(default_factory=list)

    extras: dict = field(default_factory=dict)
    run_history: List[str] = field(default_factory=list)

    @property
    def prefix(self) -> str:
        return f"[{self.label}] " if self.label else ""

    def require(self, *stage_names: str) -> None:
        missing = [name for name in stage_names if name not in self.run_history]
        if missing:
            raise RuntimeError(
                f"stage(s) {missing} must run before this one; "
                f"history so far: {self.run_history or ['<empty>']}"
            )
