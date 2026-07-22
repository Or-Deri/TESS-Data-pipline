"""Registry + factory for dehazing strategies.

Strategies self-register by ``label`` with the :func:`register_strategy` class
decorator; :func:`create_dehazer` builds one by name. This lets a surrounding
pipeline add algorithms without touching any existing code.
"""

from __future__ import annotations

from typing import Dict, List, Type

from .base import BaseDehazer

_REGISTRY: Dict[str, Type[BaseDehazer]] = {}


def register_strategy(cls: Type[BaseDehazer]) -> Type[BaseDehazer]:
    """Class decorator registering a strategy under its ``label``."""
    label = getattr(cls, "label", "")
    if not label:
        raise ValueError(f"{cls.__name__} must define a non-empty 'label'")
    if label in _REGISTRY and _REGISTRY[label] is not cls:
        raise ValueError(f"strategy label {label!r} is already registered")
    _REGISTRY[label] = cls
    return cls


def available_strategies() -> List[str]:
    """Sorted list of registered strategy labels (e.g. ``['3d']``)."""
    return sorted(_REGISTRY)


def create_dehazer(label: str, **kwargs) -> BaseDehazer:
    """Factory: instantiate a registered strategy by label."""
    try:
        cls = _REGISTRY[label]
    except KeyError:
        raise ValueError(
            f"unknown dehazing strategy {label!r}; "
            f"available: {available_strategies()}"
        ) from None
    return cls(**kwargs)
