"""Pluggable dehazing algorithms for embedding in a larger pipeline.

Design patterns: **Protocol** (`Dehazer`), **Strategy** + **Template Method**
(`BaseDehazer` and concretes), **Registry / Factory** (`register_strategy`,
`create_dehazer`, `available_strategies`), and **Context** (`DehazingContext`).

Importing this package registers the built-in default strategy as a side
effect, so :func:`available_strategies` and :func:`create_dehazer` work
immediately.

Example::

    from paloma.cleaning.dehazer import DehazingContext, DehazeConfig

    result = DehazingContext.default().execute(in_dir, out_dir, DehazeConfig())
    print(result.num_outputs, "frames ->", result.output_dir)
"""

from .base import BaseDehazer, Dehazer, DehazeResult
from .context import DehazingContext

# Importing the concrete strategy triggers its registration.
from .dehazing import DehazingStrategy
from .registry import (
    _REGISTRY,
    available_strategies,
    create_dehazer,
    register_strategy,
)

__all__ = [
    "Dehazer",
    "BaseDehazer",
    "DehazeResult",
    "DehazingContext",
    "DehazingStrategy",
    "register_strategy",
    "create_dehazer",
    "available_strategies",
]
