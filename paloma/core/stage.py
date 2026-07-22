"""The common pipeline-stage interface.

Every processing step implements :class:`PipelineStage`. Cleaning owns a real
stage; other stages are shields that raise :class:`NotImplementedError`.

A stage may return ``None`` to stop the chain early.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar

TIn = TypeVar("TIn")
TOut = TypeVar("TOut")


class PipelineStage(ABC, Generic[TIn, TOut]):
    """One ordered step: ``run(input) -> output``.

    Subclasses set :attr:`name` and implement :meth:`run`. Returning ``None``
    signals the caller to stop early.
    """

    name: str = ""

    @abstractmethod
    def run(self, data: TIn) -> Optional[TOut]:
        """Transform ``data`` and return the result, or ``None`` to stop."""

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<{type(self).__name__} name={self.name!r}>"
