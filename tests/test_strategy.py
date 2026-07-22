"""Tests for the pluggable dehazing strategy layer (Protocol / Strategy / Factory)."""

import pytest

from conftest import assert_outputs_match
from paloma.cleaning.dehazer.config import DehazeConfig
from paloma.cleaning.dehazer.strategies import (
    BaseDehazer,
    DehazeResult,
    Dehazer,
    DehazingContext,
    DehazingStrategy,
    available_strategies,
    create_dehazer,
    register_strategy,
)


def test_registry_lists_builtin_strategies():
    assert available_strategies() == ["default"]


def test_concrete_strategies_satisfy_protocol():
    assert isinstance(DehazingStrategy(), Dehazer)


def test_factory_creates_by_label():
    assert isinstance(create_dehazer("default"), DehazingStrategy)


def test_factory_rejects_unknown_label():
    with pytest.raises(ValueError, match="unknown dehazing strategy"):
        create_dehazer("nope")


def test_register_rejects_missing_label():
    with pytest.raises(ValueError, match="non-empty 'label'"):
        @register_strategy
        class _NoLabel(BaseDehazer):
            def _run(self, input_dir, output_dir, cfg):
                pass


def test_register_rejects_duplicate_label():
    with pytest.raises(ValueError, match="already registered"):
        @register_strategy
        class _Dup(BaseDehazer):
            label = "default"

            def _run(self, input_dir, output_dir, cfg):
                pass


def test_context_execute_returns_result(synthetic_fits, cfg_kwargs, tmp_path):
    out = tmp_path / "out"
    result = DehazingContext.default().execute(
        str(synthetic_fits), str(out), DehazeConfig(**cfg_kwargs)
    )
    assert isinstance(result, DehazeResult)
    assert result.label == "default"
    assert result.num_outputs == cfg_kwargs["num_frames"]
    assert all(p.endswith(".fits") for p in result.outputs)


def test_context_set_strategy_swaps_algorithm(synthetic_fits, cfg_kwargs, tmp_path):
    class _Sentinel(BaseDehazer):
        label = "sentinel"

        def _run(self, input_dir, output_dir, cfg):
            raise AssertionError("swapped-out strategy should not run")

    ctx = DehazingContext(_Sentinel())
    assert ctx.strategy.label == "sentinel"
    ctx.set_strategy(DehazingStrategy())
    assert ctx.strategy.label == "default"

    out = tmp_path / "out"
    result = ctx.execute(str(synthetic_fits), str(out), DehazeConfig(**cfg_kwargs))
    assert result.label == "default"
    assert result.num_outputs == cfg_kwargs["num_frames"]


def test_strategy_output_matches_direct_run(synthetic_fits, cfg_kwargs, tmp_path):
    """The strategy wrapper must be a no-op over dehaze() (identical FITS)."""
    from paloma.cleaning.dehazer.pipeline import dehaze

    out_direct = tmp_path / "direct"
    out_strategy = tmp_path / "strategy"

    dehaze(str(synthetic_fits), str(out_direct), DehazeConfig(**cfg_kwargs))
    DehazingContext.default().execute(
        str(synthetic_fits), str(out_strategy), DehazeConfig(**cfg_kwargs)
    )

    assert_outputs_match(out_direct, out_strategy)


def test_custom_strategy_can_be_registered_and_used(tmp_path):
    from paloma.cleaning.dehazer.strategies import _REGISTRY

    @register_strategy
    class _Noop(BaseDehazer):
        label = "noop-test"

        def _run(self, input_dir, output_dir, cfg):
            import os
            os.makedirs(output_dir, exist_ok=True)

    try:
        assert "noop-test" in available_strategies()
        result = create_dehazer("noop-test").run(
            "in", str(tmp_path / "out_noop"), DehazeConfig()
        )
        assert result.label == "noop-test"
        assert result.num_outputs == 0
    finally:
        _REGISTRY.pop("noop-test", None)
