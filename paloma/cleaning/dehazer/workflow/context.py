"""The mutable state object threaded through a chain of stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

import numpy as np


@dataclass
class WorkflowContext:
    """Mutable state threaded through a chain of stages.

    A single context flows through every stage of one run (one batch of the 3-D
    pipeline). Stages populate the fields they produce and read the fields they
    depend on; the ``run_history`` records the stages that have executed, which
    downstream stages use to enforce ordering.
    """

    cfg: Any
    use_gpu: bool = False

    # Run-scoped inputs
    input_dir: Optional[str] = None
    output_dir: Optional[str] = None
    label: str = ""

    # Array module for the device the data currently lives on
    xp: Any = np

    # Batch artifacts produced along the chain
    cube: Any = None
    metadata: Optional[List[dict]] = None
    raw_airlights: Optional[List[float]] = None
    airlights: Any = None
    t_cube: Any = None

    # Free-form scratch space + bookkeeping
    extras: dict = field(default_factory=dict)
    run_history: List[str] = field(default_factory=list)

    @property
    def prefix(self) -> str:
        """Progress-message prefix, e.g. ``"[Batch 2/5] "``."""
        return f"[{self.label}] " if self.label else ""

    def require(self, *stage_names: str) -> None:
        """Raise if any prerequisite stage has not run in this context.

        This is what keeps the workflow honest: the 3-D steps must run in order
        (airlight -> smoothing -> transmission -> recovery) and each stage
        declares the stages it depends on.
        """
        missing = [name for name in stage_names if name not in self.run_history]
        if missing:
            raise RuntimeError(
                f"stage(s) {missing} must run before this one; "
                f"history so far: {self.run_history or ['<empty>']}"
            )
