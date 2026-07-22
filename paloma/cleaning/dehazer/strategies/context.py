"""The Strategy-pattern Context that holds and delegates to a dehazer."""

from __future__ import annotations

from ..config import DehazeConfig
from .base import Dehazer, DehazeResult
from .registry import create_dehazer

#: Label of the built-in default dehazing strategy.
DEFAULT_STRATEGY = "default"


class DehazingContext:
    """Holds the active strategy and delegates execution to it.

    This is the object the surrounding pipeline talks to; it depends only on the
    :class:`Dehazer` protocol and never on a concrete algorithm.
    """

    def __init__(self, strategy: Dehazer) -> None:
        self._strategy = strategy

    @classmethod
    def from_label(cls, label: str, **kwargs) -> "DehazingContext":
        """Build a context around a strategy created from the registry."""
        return cls(create_dehazer(label, **kwargs))

    @classmethod
    def default(cls, **kwargs) -> "DehazingContext":
        """Build a context around the built-in default dehazing strategy."""
        return cls(create_dehazer(DEFAULT_STRATEGY, **kwargs))

    @property
    def strategy(self) -> Dehazer:
        return self._strategy

    def set_strategy(self, strategy: Dehazer) -> "DehazingContext":
        """Swap the active strategy at runtime; returns self for chaining."""
        self._strategy = strategy
        return self

    def execute(self, input_dir: str, output_dir: str, cfg: DehazeConfig) -> DehazeResult:
        return self._strategy.run(input_dir, output_dir, cfg)
