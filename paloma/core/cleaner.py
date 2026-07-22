"""The pipeline-level cleaning abstraction.

The **Cleaning** stage does not hard-code a single algorithm. Instead it is
defined against a small interface, :class:`Cleaner`, and any number of cleaning
algorithms can implement it. The active cleaner is chosen by
:class:`~paloma.config.CleaningConfig` (by name), so new cleaners are added by
*writing* code, never by *modifying* the stage.

Design patterns (mirroring the dehazer's own Strategy layer, one level up):

* **Protocol** (:class:`Cleaner`) — the structural interface the stage depends on.
* **Strategy / Template Method** (:class:`BaseCleaner`) — base class for
  concrete cleaners.
* **Registry / Factory** (:func:`register_cleaner`, :func:`create_cleaner`,
  :func:`available_cleaners`) — cleaners self-register by ``name`` and are built
  by name from configuration.

The first cleaner is
:class:`~paloma.cleaning.dehazer_cleaner.DehazerCleaner` (name ``"dehazer"``);
more cleaning algorithms can be registered alongside it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Dict, List, Optional, Protocol, Type, runtime_checkable

from .types import CleaningRequest, CleaningResult


@runtime_checkable
class Cleaner(Protocol):
    """Structural interface every cleaning algorithm satisfies.

    Depend on this protocol (not on a concrete cleaner) when wiring cleaning
    into the pipeline.
    """

    name: str

    def clean(self, request: CleaningRequest) -> Optional[CleaningResult]:
        """Clean the data described by ``request``.

        Returns a :class:`CleaningResult`, or ``None`` to stop the pipeline
        (chain-of-responsibility) when nothing usable was produced.
        """
        ...


class BaseCleaner(ABC):
    """Base class for concrete cleaners implementing :class:`Cleaner`.

    Subclasses set the :attr:`name` class attribute and implement
    :meth:`clean`.
    """

    name: ClassVar[str] = ""

    @abstractmethod
    def clean(self, request: CleaningRequest) -> Optional[CleaningResult]:
        """Run the cleaning algorithm and return its result."""

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<{type(self).__name__} name={self.name!r}>"


# --- Registry / Factory -----------------------------------------------------

_REGISTRY: Dict[str, Type[BaseCleaner]] = {}


def register_cleaner(cls: Type[BaseCleaner]) -> Type[BaseCleaner]:
    """Class decorator registering a cleaner under its ``name``."""
    name = getattr(cls, "name", "")
    if not name:
        raise ValueError(f"{cls.__name__} must define a non-empty 'name'")
    if name in _REGISTRY and _REGISTRY[name] is not cls:
        raise ValueError(f"cleaner name {name!r} is already registered")
    _REGISTRY[name] = cls
    return cls


def available_cleaners() -> List[str]:
    """Sorted list of registered cleaner names (e.g. ``['dehazer']``)."""
    return sorted(_REGISTRY)


def create_cleaner(name: str, **kwargs) -> BaseCleaner:
    """Factory: instantiate a registered cleaner by name."""
    try:
        cls = _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"unknown cleaner {name!r}; available: {available_cleaners()}"
        ) from None
    return cls(**kwargs)
