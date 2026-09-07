"""Strategy registry for the image-subtraction engine."""

from __future__ import annotations

from typing import Dict, Type

from .pipeline import DefaultSubtractor

_STRATEGIES: Dict[str, Type] = {}


def register_strategy(cls):
    label = getattr(cls, "label", "")
    if not label:
        raise ValueError(f"{cls.__name__} must define label")
    _STRATEGIES[label] = cls
    return cls


def create_subtractor_strategy(label: str, **kwargs):
    if label not in _STRATEGIES:
        raise ValueError(f"unknown strategy {label!r}")
    return _STRATEGIES[label](**kwargs)


def available_strategies():
    return sorted(_STRATEGIES)


# Ensure default is registered via subtractor registry
__all__ = ["DefaultSubtractor", "register_strategy", "create_subtractor_strategy", "available_strategies"]
