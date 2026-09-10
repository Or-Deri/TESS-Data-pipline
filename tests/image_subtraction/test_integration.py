"""ImageSubtractionStage ↔ DefaultSubtractor adapter tests.

The algorithm itself is checked in ``test_groundtruth.py``. These tests stay
on the wiring: registry, config, request overrides, and result mapping.
"""

import pytest

from paloma import (
    ImageSubtractionConfig,
    ImageSubtractionStage,
    SubtractionRequest,
    SubtractionResult,
    available_subtractors,
    create_subtractor,
)
from paloma.core.subtractor import Subtractor
from paloma.image_subtraction import DefaultSubtractor, SubtractionConfig


def test_default_subtractor_registered():
    assert "default" in available_subtractors()
    s = create_subtractor("default", strategy="default", blknum=5)
    assert isinstance(s, DefaultSubtractor)
    assert isinstance(s, Subtractor)
    assert s.strategy == "default"
    assert s.params["blknum"] == 5


def test_factory_rejects_unknown_subtractor():
    with pytest.raises(ValueError, match="unknown subtractor"):
        create_subtractor("nope")


def test_stage_from_config():
    stage = ImageSubtractionStage.from_config(
        ImageSubtractionConfig(subtractor="default", params={"blknum": 5})
    )
    assert isinstance(stage.subtractor, DefaultSubtractor)
    assert stage.subtractor.name == "default"
    assert stage.subtractor.params["blknum"] == 5


def test_stage_rejects_kwargs_with_instance():
    with pytest.raises(TypeError, match="subtractor_kwargs"):
        ImageSubtractionStage(DefaultSubtractor(), blknum=5)


def test_unknown_subtraction_params_raise():
    subtractor = DefaultSubtractor(not_a_real_field=1)
    with pytest.raises(ValueError, match="Unknown SubtractionConfig parameter"):
        subtractor.subtract(
            SubtractionRequest(input_dir="in", output_dir="out")
        )


def test_build_config_from_params():
    subtractor = DefaultSubtractor(
        blknum=4,
        num_iterations=1,
        nr_stars=5,
        apply_data_quality_filter=False,
        num_frames=1,
        use_c_backend=False,
    )
    cfg = subtractor._build_config(SubtractionConfig, {**subtractor.params})
    assert cfg.blknum == 4
    assert cfg.use_c_backend is False


def test_stage_run_returns_subtraction_result(tmp_path, monkeypatch):
    out = tmp_path / "subtracted"
    out.mkdir()
    fits_path = out / "subtracted__frame.fits"
    fits_path.write_bytes(b"")
    inp = tmp_path / "in"
    fake = SubtractionResult(
        input_dir=str(inp),
        output_dir=str(out),
        outputs=[str(fits_path)],
        sources_csv=str(out / "found_sources.csv"),
        metadata={"residual_count": 1},
    )
    monkeypatch.setattr(
        "paloma.image_subtraction.pipeline.subtract", lambda *a, **k: fake
    )

    stage = ImageSubtractionStage.from_config(
        ImageSubtractionConfig(subtractor="default")
    )
    result = stage.run(
        SubtractionRequest(
            input_dir=str(inp),
            output_dir=str(out),
            metadata={"run": "integration"},
        )
    )

    assert isinstance(result, SubtractionResult)
    assert result.num_outputs == 1
    assert result.input_dir == str(inp)
    assert result.output_dir == str(out)
    assert result.outputs == [str(fits_path)]
    assert result.metadata["subtractor"] == "default"
    assert result.metadata["strategy"] == "default"
    assert result.metadata["run"] == "integration"
    assert result.metadata["residual_count"] == 1


def test_request_params_override_constructor(tmp_path, monkeypatch):
    """Per-request params win over subtractor constructor params."""
    captured = {}

    def fake_subtract(input_dir, output_dir, cfg):
        captured["blknum"] = cfg.blknum
        return SubtractionResult(
            input_dir=input_dir,
            output_dir=output_dir,
            outputs=[str(tmp_path / "subtracted__x.fits")],
        )

    monkeypatch.setattr("paloma.image_subtraction.pipeline.subtract", fake_subtract)
    stage = ImageSubtractionStage("default", blknum=4)
    result = stage.run(
        SubtractionRequest(
            input_dir=str(tmp_path / "in"),
            output_dir=str(tmp_path / "out"),
            params={"blknum": 5},
        )
    )
    assert result is not None
    assert captured["blknum"] == 5


def test_empty_outputs_stop_pipeline(monkeypatch, tmp_path):
    """Chain-of-responsibility: zero residuals → ImageSubtractionStage returns None."""
    empty = SubtractionResult(
        input_dir=str(tmp_path / "in"),
        output_dir=str(tmp_path / "out"),
        outputs=[],
    )
    monkeypatch.setattr(
        "paloma.image_subtraction.pipeline.subtract",
        lambda *a, **k: empty,
    )

    stage = ImageSubtractionStage("default")
    result = stage.run(
        SubtractionRequest(
            input_dir=str(tmp_path / "in"), output_dir=str(tmp_path / "out")
        )
    )
    assert result is None
