"""Unit tests for the shared ``paloma.core.chain`` engine."""

import pytest

from paloma.core.chain import Chain, FunctionStage, Stage, as_stage


class _Ctx:
    def __init__(self):
        self.extras = {}
        self.run_history = []

    def require(self, *stage_names):
        missing = [name for name in stage_names if name not in self.run_history]
        if missing:
            raise RuntimeError(
                f"stage(s) {missing} must run before this one; "
                f"history so far: {self.run_history or ['<empty>']}"
            )


class _Append(Stage):
    def __init__(self, tag, requires=()):
        self.name = tag
        self.requires = requires

    def apply(self, ctx):
        ctx.extras.setdefault("order", []).append(self.name)
        return ctx


def test_rshift_composes_stages_into_a_chain():
    chain = _Append("a") >> _Append("b") >> _Append("c")
    assert isinstance(chain, Chain)
    assert len(chain) == 3


def test_chain_runs_stages_in_order():
    ctx = (_Append("a") >> _Append("b") >> _Append("c")).run(_Ctx())
    assert ctx.extras["order"] == ["a", "b", "c"]
    assert ctx.run_history == ["a", "b", "c"]


def test_chains_concatenate_and_flatten():
    left = _Append("a") >> _Append("b")
    right = _Append("c") >> _Append("d")
    combined = left >> right
    assert len(combined) == 4
    ctx = combined.run(_Ctx())
    assert ctx.extras["order"] == ["a", "b", "c", "d"]


def test_plain_callable_is_wrapped_as_stage():
    def bump(ctx):
        ctx.extras["bumped"] = True
        return ctx

    chain = _Append("a") >> bump
    assert isinstance(chain.stages[-1], FunctionStage)
    ctx = chain.run(_Ctx())
    assert ctx.extras["bumped"] is True


def test_function_stage_may_return_none_and_context_is_preserved():
    @as_stage(name="mutate")
    def mutate(ctx):
        ctx.extras["x"] = 1

    ctx = Chain([mutate]).run(_Ctx())
    assert ctx.extras["x"] == 1
    assert ctx.run_history == ["mutate"]


def test_requires_guard_raises_when_prerequisite_missing():
    guarded = _Append("needs_a", requires=("a",))
    with pytest.raises(RuntimeError, match="must run before"):
        guarded.run(_Ctx())


def test_requires_guard_passes_when_prerequisite_ran():
    ctx = (_Append("a") >> _Append("needs_a", requires=("a",))).run(_Ctx())
    assert ctx.run_history == ["a", "needs_a"]
