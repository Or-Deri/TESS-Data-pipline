"""The composable stage/chain engine.

A :class:`Chain` is an ordered sequence of :class:`Stage` objects that each
transform a shared :class:`WorkflowContext` and return it. Stages compose with
the ``>>`` operator::

    chain = StageA() >> StageB() >> StageC()
    ctx = chain.run(WorkflowContext(cfg=cfg))

A :class:`Chain` is itself a :class:`Stage`, so chains nest and concatenate
freely. Plain callables ``fn(ctx) -> ctx | None`` are wrapped automatically.

This module has no dehazing-specific logic; the concrete stages live in
:mod:`tess_dehazing.workflow.stages`.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Iterator, List, Optional

from .context import WorkflowContext


class Stage:
    """A single, composable step in a workflow.

    Subclasses implement :meth:`apply`; they should not usually override
    :meth:`run`, which handles bookkeeping (ordering guard, history) around
    :meth:`apply`.
    """

    #: Stable identifier used for ordering guards and logging.
    name: str = "stage"
    #: Names of stages that must have run earlier in the same context.
    requires: tuple = ()

    def apply(self, ctx: WorkflowContext) -> Optional[WorkflowContext]:
        raise NotImplementedError

    def run(self, ctx: WorkflowContext) -> WorkflowContext:
        if self.requires:
            ctx.require(*self.requires)
        result = self.apply(ctx)
        if isinstance(result, WorkflowContext):
            ctx = result
        ctx.run_history.append(self.name)
        return ctx

    # -- composition ---------------------------------------------------------
    def __rshift__(self, other: Any) -> "Chain":
        return Chain([self]) >> other

    def __call__(self, ctx: WorkflowContext) -> WorkflowContext:
        return self.run(ctx)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<Stage {self.name}>"


class FunctionStage(Stage):
    """Adapter that turns a plain ``fn(ctx) -> ctx | None`` into a Stage."""

    def __init__(self, fn: Callable[[WorkflowContext], Any], name: Optional[str] = None):
        self.fn = fn
        self.name = name or getattr(fn, "__name__", "fn")

    def apply(self, ctx: WorkflowContext) -> Optional[WorkflowContext]:
        return self.fn(ctx)


def as_stage(fn: Optional[Callable] = None, *, name: Optional[str] = None):
    """Decorator / wrapper making a function usable inside a chain.

    Usage::

        @as_stage(name="my_step")
        def my_step(ctx):
            ...
            return ctx
    """
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

    def apply(self, ctx: WorkflowContext) -> WorkflowContext:
        for stage in self.stages:
            ctx = stage.run(ctx)
        return ctx

    # A chain adds its members to history individually (via their own run),
    # so it should not also append its own name.
    def run(self, ctx: WorkflowContext) -> WorkflowContext:
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
