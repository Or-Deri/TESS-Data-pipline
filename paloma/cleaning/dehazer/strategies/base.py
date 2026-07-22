"""The dehazing strategy interface and its result object.

Design patterns:
- **Protocol** (:class:`Dehazer`) — a structural interface callers depend on.
- **Strategy / Template Method** (:class:`BaseDehazer`) — the base fixes the
  "run then collect a result" skeleton; subclasses implement ``_run``.
"""

from __future__ import annotations

import glob
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar, List, Protocol, runtime_checkable

from ..config import DehazeConfig
from ..io import DEHAZED_PREFIX


@dataclass
class DehazeResult:
    """Outcome of a dehazing run, for the surrounding pipeline to consume."""

    label: str
    input_dir: str
    output_dir: str
    outputs: List[str] = field(default_factory=list)

    @property
    def num_outputs(self) -> int:
        return len(self.outputs)

    @classmethod
    def collect(cls, label: str, input_dir: str, output_dir: str) -> "DehazeResult":
        """Build a result by scanning ``output_dir`` for this run's FITS files."""
        pattern = os.path.join(os.path.abspath(output_dir), f"{DEHAZED_PREFIX}*.fits")
        outputs = sorted(glob.glob(pattern))
        return cls(
            label=label,
            input_dir=os.path.abspath(input_dir),
            output_dir=os.path.abspath(output_dir),
            outputs=outputs,
        )


@runtime_checkable
class Dehazer(Protocol):
    """Structural interface every dehazing algorithm satisfies.

    Depend on this protocol (not on concrete strategy classes) when integrating
    dehazing into a larger pipeline.
    """

    label: str

    def run(self, input_dir: str, output_dir: str, cfg: DehazeConfig) -> DehazeResult:
        ...


class BaseDehazer(ABC):
    """Strategy base class implementing the :class:`Dehazer` protocol.

    Subclasses set the ``label`` class attribute and implement :meth:`_run`.
    :meth:`run` is a template method: it runs the algorithm then collects a
    :class:`DehazeResult`, so every strategy reports its output uniformly.
    """

    label: ClassVar[str] = ""

    @abstractmethod
    def _run(self, input_dir: str, output_dir: str, cfg: DehazeConfig) -> None:
        """Execute the algorithm, writing dehazed FITS into ``output_dir``."""

    def run(self, input_dir: str, output_dir: str, cfg: DehazeConfig) -> DehazeResult:
        self._run(input_dir, output_dir, cfg)
        return DehazeResult.collect(self.label, input_dir, output_dir)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<{type(self).__name__} label={self.label!r}>"
