"""Shared composable stage/chain engine (``>>``).

A :class:`Chain` is an ordered sequence of :class:`Stage` objects that each
transform a shared context and return it. Stages compose with ``>>``::

    chain = StageA() >> StageB() >> StageC()
    ctx = chain.run(ctx)

Contexts must support ``require(*names)`` and ``run_history`` (a list).
Concrete workflow contexts live under each engine's ``workflow`` package.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Iterator, List, Optional


class Stage:
    """A single, composable step in a workflow.

    Subclasses implement :meth:`apply`; they should not usually override
    :meth:`run`, which handles bookkeeping (ordering guard, history) around
    :meth:`apply`.
    """

    name: str = "stage"
    requires: tuple = ()

    def apply(self, ctx: Any) -> Optional[Any]:
        raise NotImplementedError

    def run(self, ctx: Any) -> Any:
        if self.requires:
            ctx.require(*self.requires)
        result = self.apply(ctx)
        if result is not None:
            ctx = result
        ctx.run_history.append(self.name)
        return ctx

    def __rshift__(self, other: Any) -> "Chain":
        return Chain([self]) >> other

    def __call__(self, ctx: Any) -> Any:
        return self.run(ctx)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<Stage {self.name}>"


class FunctionStage(Stage):
    """Adapter that turns a plain ``fn(ctx) -> ctx | None`` into a Stage."""

    def __init__(self, fn: Callable[[Any], Any], name: Optional[str] = None):
        self.fn = fn
        self.name = name or getattr(fn, "__name__", "fn")

    def apply(self, ctx: Any) -> Optional[Any]:
        return self.fn(ctx)


def as_stage(fn: Optional[Callable] = None, *, name: Optional[str] = None):
    """Decorator / wrapper making a function usable inside a chain."""
    if fn is None:
        return lambda f: FunctionStage(f, name)
    return FunctionStage(fn, name)


def _coerce(obj: Any) -> Stage:
    if isinstance(obj, Stage):
        return obj
    if callable(obj):
        return FunctionStage(obj)
    raise TypeError(f"cannot use {obj!r} as a workflow stage")


class Chain(Stage):
    """An ordered, composable sequence of stages that is itself a stage."""

    def __init__(self, stages: Optional[List[Any]] = None, name: str = "chain"):
        self.stages: List[Stage] = [_coerce(s) for s in (stages or [])]
        self.name = name

    def __rshift__(self, other: Any) -> "Chain":
        if isinstance(other, Chain):
            return Chain(self.stages + other.stages, name=self.name)
        return Chain(self.stages + [_coerce(other)], name=self.name)

    def then(self, other: Any) -> "Chain":
        """Fluent alias for the ``>>`` operator."""
        return self >> other

    def apply(self, ctx: Any) -> Any:
        for stage in self.stages:
            ctx = stage.run(ctx)
        return ctx

    def run(self, ctx: Any) -> Any:
        if self.requires:
            ctx.require(*self.requires)
        return self.apply(ctx)

    def __iter__(self) -> Iterator[Stage]:
        return iter(self.stages)

    def __len__(self) -> int:
        return len(self.stages)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        inner = " >> ".join(s.name for s in self.stages)
        return f"Chain({inner})"


class timed:  # noqa: N801 - used as a context helper
    """Context manager that prints ``label`` and its wall-clock duration."""

    def __init__(self, label: str, enabled: bool = True):
        self.label = label
        self.enabled = enabled
        self._start = 0.0

    def __enter__(self) -> "timed":
        self._start = time.time()
        if self.enabled and self.label:
            print(self.label)
        return self

    def __exit__(self, *exc: Any) -> None:
        if self.enabled:
            print(f"  completed in {time.time() - self._start:.1f}s")
