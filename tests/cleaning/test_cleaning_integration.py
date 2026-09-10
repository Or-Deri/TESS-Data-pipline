"""Pipeline cleaning ↔ dehazer integration (Cleaner / CleaningStage).

These tests cover the adapter path:
``CleaningStage`` → ``DehazerCleaner`` → ``dehaze``.
They stay on the synthetic fixtures — no second ground-truth run.
"""

from unittest.mock import MagicMock

import pytest

from tests.cleaning.helpers import assert_outputs_match
from paloma import (
    CleaningConfig,
    CleaningRequest,
    CleaningResult,
    CleaningStage,
    Cleaner,
    DehazerCleaner,
    available_cleaners,
    create_cleaner,
)
from paloma.cleaning.dehazer import DehazeConfig, DehazeResult, dehaze


def test_dehazer_is_registered():
    assert "dehazer" in available_cleaners()
    cleaner = create_cleaner("dehazer")
    assert isinstance(cleaner, DehazerCleaner)
    assert isinstance(cleaner, Cleaner)


def test_factory_rejects_unknown_cleaner():
    with pytest.raises(ValueError, match="unknown cleaner"):
        create_cleaner("nope")


def test_cleaning_stage_from_config():
    stage = CleaningStage.from_config(
        CleaningConfig(cleaner="dehazer", params={"strategy": "default", "num_frames": 4})
    )
    assert isinstance(stage.cleaner, DehazerCleaner)
    assert stage.cleaner.strategy == "default"
    assert stage.cleaner.params["num_frames"] == 4


def test_cleaning_stage_rejects_kwargs_with_instance():
    with pytest.raises(TypeError, match="cleaner_kwargs"):
        CleaningStage(DehazerCleaner(), num_frames=4)


def test_unknown_dehaze_params_raise():
    cleaner = DehazerCleaner(not_a_real_field=1)
    with pytest.raises(ValueError, match="Unknown DehazeConfig parameter"):
        cleaner.clean(
            CleaningRequest(input_dir="in", output_dir="out")
        )


def test_stage_run_returns_cleaning_result(synthetic_fits, cfg_kwargs, tmp_path):
    out = tmp_path / "cleaned"
    stage = CleaningStage.from_config(
        CleaningConfig(cleaner="dehazer", params=dict(cfg_kwargs))
    )
    result = stage.run(
        CleaningRequest(
            input_dir=str(synthetic_fits),
            output_dir=str(out),
            metadata={"run": "integration"},
        )
    )

    assert isinstance(result, CleaningResult)
    assert result.num_outputs == cfg_kwargs["num_frames"]
    assert result.input_dir == str(synthetic_fits.resolve())
    assert result.output_dir == str(out.resolve())
    assert all(p.endswith(".fits") for p in result.outputs)
    assert result.metadata["cleaner"] == "dehazer"
    assert result.metadata["strategy"] == "default"
    assert result.metadata["run"] == "integration"


def test_stage_matches_direct_dehaze(synthetic_fits, cfg_kwargs, tmp_path):
    """CleaningStage through DehazerCleaner must match dehaze() pixel-for-pixel."""
    out_stage = tmp_path / "stage"
    out_direct = tmp_path / "direct"

    stage = CleaningStage.from_config(
        CleaningConfig(cleaner="dehazer", params=dict(cfg_kwargs))
    )
    stage.run(
        CleaningRequest(input_dir=str(synthetic_fits), output_dir=str(out_stage))
    )
    dehaze(str(synthetic_fits), str(out_direct), DehazeConfig(**cfg_kwargs))

    assert_outputs_match(out_stage, out_direct)


def test_request_params_override_constructor(synthetic_fits, cfg_kwargs, tmp_path):
    """Per-request params win over cleaner constructor params."""
    out = tmp_path / "out"
    ctor = dict(cfg_kwargs)
    ctor["num_frames"] = 2
    stage = CleaningStage("dehazer", **ctor)

    result = stage.run(
        CleaningRequest(
            input_dir=str(synthetic_fits),
            output_dir=str(out),
            params={"num_frames": cfg_kwargs["num_frames"]},
        )
    )
    assert result is not None
    assert result.num_outputs == cfg_kwargs["num_frames"]


def test_empty_outputs_stop_pipeline(monkeypatch, tmp_path):
    """Chain-of-responsibility: zero cleaned frames → CleaningStage returns None."""
    empty = DehazeResult(
        label="default",
        input_dir=str(tmp_path / "in"),
        output_dir=str(tmp_path / "out"),
        outputs=[],
    )
    monkeypatch.setattr(
        "paloma.cleaning.dehazer.runner.dehaze",
        lambda *a, **k: empty,
    )

    stage = CleaningStage("dehazer")
    result = stage.run(
        CleaningRequest(input_dir=str(tmp_path / "in"), output_dir=str(tmp_path / "out"))
    )
    assert result is None
