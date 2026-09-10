"""CleaningStage ↔ DehazerCleaner adapter tests.

The algorithm itself is checked in ``test_groundtruth.py``. These tests stay
on the wiring: registry, config, request overrides, and result mapping.
"""

import pytest

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
from paloma.cleaning.dehazer import DehazeResult


def test_dehazer_is_registered():
    assert "dehazer" in available_cleaners()
    cleaner = create_cleaner("dehazer", strategy="default", num_frames=2)
    assert isinstance(cleaner, DehazerCleaner)
    assert isinstance(cleaner, Cleaner)
    assert cleaner.strategy == "default"
    assert cleaner.params["num_frames"] == 2


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


def test_dehaze_result_collect(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "dehazed__a.fits").write_bytes(b"")
    (out / "other.fits").write_bytes(b"")
    result = DehazeResult.collect("default", str(tmp_path / "in"), str(out))
    assert result.num_outputs == 1
    assert result.outputs[0].endswith("dehazed__a.fits")


def test_stage_run_returns_cleaning_result(tmp_path, monkeypatch):
    out = tmp_path / "cleaned"
    out.mkdir()
    fits_path = out / "dehazed__frame.fits"
    fits_path.write_bytes(b"")
    inp = tmp_path / "in"
    fake = DehazeResult(
        label="default",
        input_dir=str(inp),
        output_dir=str(out),
        outputs=[str(fits_path)],
    )
    monkeypatch.setattr("paloma.cleaning.dehazer.runner.dehaze", lambda *a, **k: fake)

    stage = CleaningStage.from_config(CleaningConfig(cleaner="dehazer"))
    result = stage.run(
        CleaningRequest(
            input_dir=str(inp),
            output_dir=str(out),
            metadata={"run": "integration"},
        )
    )

    assert isinstance(result, CleaningResult)
    assert result.num_outputs == 1
    assert result.input_dir == str(inp)
    assert result.output_dir == str(out)
    assert result.outputs == [str(fits_path)]
    assert result.metadata["cleaner"] == "dehazer"
    assert result.metadata["strategy"] == "default"
    assert result.metadata["run"] == "integration"


def test_request_params_override_constructor(tmp_path, monkeypatch):
    """Per-request params win over cleaner constructor params."""
    captured = {}

    def fake_dehaze(input_dir, output_dir, cfg):
        captured["num_frames"] = cfg.num_frames
        return DehazeResult(
            label="default",
            input_dir=input_dir,
            output_dir=output_dir,
            outputs=[str(tmp_path / "dehazed__x.fits")],
        )

    monkeypatch.setattr("paloma.cleaning.dehazer.runner.dehaze", fake_dehaze)
    stage = CleaningStage("dehazer", num_frames=2)
    result = stage.run(
        CleaningRequest(
            input_dir=str(tmp_path / "in"),
            output_dir=str(tmp_path / "out"),
            params={"num_frames": 4},
        )
    )
    assert result is not None
    assert captured["num_frames"] == 4


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
