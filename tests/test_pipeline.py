"""Pipeline orchestrator: Cleaning → Image Subtraction chaining."""

from __future__ import annotations

from unittest.mock import MagicMock

from paloma import (
    CleaningConfig,
    CleaningRequest,
    CleaningResult,
    CleaningStage,
    ImageSubtractionConfig,
    ImageSubtractionStage,
    Pipeline,
    PipelineConfig,
    SubtractionResult,
)


def test_pipeline_chains_cleaning_then_subtraction(tmp_path):
    cleaned_out = tmp_path / "cleaned"
    subtracted_out = tmp_path / "subtracted"
    cleaned_out.mkdir()
    (cleaned_out / "frame.fits").write_text("stub")

    cleaning_result = CleaningResult(
        input_dir=str(tmp_path / "raw"),
        output_dir=str(cleaned_out),
        outputs=[str(cleaned_out / "frame.fits")],
        metadata={"cleaner": "dehazer"},
    )
    subtraction_result = SubtractionResult(
        input_dir=str(cleaned_out),
        output_dir=str(subtracted_out),
        outputs=[str(subtracted_out / "residual.fits")],
        sources_csv=str(subtracted_out / "sources.csv"),
    )

    cleaning_stage = MagicMock(spec=CleaningStage)
    cleaning_stage.run.return_value = cleaning_result
    subtraction_stage = MagicMock(spec=ImageSubtractionStage)
    subtraction_stage.run_after_cleaning.return_value = subtraction_result

    pipeline = Pipeline(
        cleaning_stage,
        subtraction_stage,
        PipelineConfig(
            input_dir=str(tmp_path / "raw"),
            output_dir=str(tmp_path),
            cleaned_dir=str(cleaned_out),
            subtracted_dir=str(subtracted_out),
        ),
    )
    result = pipeline.run()

    assert result.ok
    assert result.cleaning is cleaning_result
    assert result.subtraction is subtraction_result
    cleaning_stage.run.assert_called_once()
    req = cleaning_stage.run.call_args[0][0]
    assert isinstance(req, CleaningRequest)
    assert req.input_dir == str(tmp_path / "raw")
    assert req.output_dir == str(cleaned_out)
    subtraction_stage.run_after_cleaning.assert_called_once_with(
        cleaning_result, str(subtracted_out)
    )


def test_pipeline_stops_when_cleaning_returns_none(tmp_path):
    cleaning_stage = MagicMock(spec=CleaningStage)
    cleaning_stage.run.return_value = None
    subtraction_stage = MagicMock(spec=ImageSubtractionStage)

    pipeline = Pipeline(
        cleaning_stage,
        subtraction_stage,
        PipelineConfig(input_dir=str(tmp_path), output_dir=str(tmp_path)),
    )
    result = pipeline.run()

    assert not result.ok
    assert result.cleaning is None
    assert result.subtraction is None
    subtraction_stage.run_after_cleaning.assert_not_called()


def test_pipeline_records_cleaning_when_subtraction_returns_none(tmp_path):
    cleaning_result = CleaningResult(
        input_dir=str(tmp_path / "raw"),
        output_dir=str(tmp_path / "cleaned"),
        outputs=[str(tmp_path / "cleaned" / "frame.fits")],
    )
    cleaning_stage = MagicMock(spec=CleaningStage)
    cleaning_stage.run.return_value = cleaning_result
    subtraction_stage = MagicMock(spec=ImageSubtractionStage)
    subtraction_stage.run_after_cleaning.return_value = None

    pipeline = Pipeline(
        cleaning_stage,
        subtraction_stage,
        PipelineConfig(input_dir=str(tmp_path / "raw"), output_dir=str(tmp_path)),
    )
    result = pipeline.run()

    assert not result.ok
    assert result.cleaning is cleaning_result
    assert result.subtraction is None
    subtraction_stage.run_after_cleaning.assert_called_once()


def test_pipeline_from_config_builds_real_stages():
    pipeline = Pipeline.from_config(
        PipelineConfig(
            cleaning=CleaningConfig(cleaner="dehazer", params={"num_frames": 2}),
            subtraction=ImageSubtractionConfig(
                subtractor="default", params={"blknum": 5}
            ),
            input_dir="in",
            output_dir="out",
        )
    )
    assert isinstance(pipeline.cleaning, CleaningStage)
    assert isinstance(pipeline.subtraction, ImageSubtractionStage)
    assert pipeline.cleaning.cleaner.name == "dehazer"
    assert pipeline.subtraction.subtractor.name == "default"
