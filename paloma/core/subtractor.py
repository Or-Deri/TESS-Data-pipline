"""The pipeline-level image-subtraction abstraction.

Image subtraction runs as its own stage *after* cleaning — it is not a
:class:`~paloma.core.cleaner.Cleaner`. Algorithms implement :class:`Subtractor`
and are selected via :class:`~paloma.config.ImageSubtractionConfig`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Dict, List, Optional, Protocol, Type, runtime_checkable

from .types import SubtractionRequest, SubtractionResult


@runtime_checkable
class Subtractor(Protocol):
    """Structural interface every image-subtraction algorithm satisfies."""

    name: str

    def subtract(self, request: SubtractionRequest) -> Optional[SubtractionResult]:
        """Run subtraction; return ``None`` when nothing usable was produced."""
        ...


class BaseSubtractor(ABC):
    """Base class for concrete subtractors."""

    name: ClassVar[str] = ""

    @abstractmethod
    def subtract(self, request: SubtractionRequest) -> Optional[SubtractionResult]:
        """Run the subtraction algorithm."""


_REGISTRY: Dict[str, Type[BaseSubtractor]] = {}


def register_subtractor(cls: Type[BaseSubtractor]) -> Type[BaseSubtractor]:
    name = getattr(cls, "name", "")
    if not name:
        raise ValueError(f"{cls.__name__} must define a non-empty 'name'")
    if name in _REGISTRY and _REGISTRY[name] is not cls:
        raise ValueError(f"subtractor name {name!r} is already registered")
    _REGISTRY[name] = cls
    return cls


def available_subtractors() -> List[str]:
    return sorted(_REGISTRY)


def create_subtractor(name: str, **kwargs) -> BaseSubtractor:
    try:
        cls = _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"unknown subtractor {name!r}; available: {available_subtractors()}"
        ) from None
    return cls(**kwargs)
