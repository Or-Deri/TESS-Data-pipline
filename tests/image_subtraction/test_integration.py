"""ImageSubtractionStage integration tests."""

from paloma import (
    ImageSubtractionConfig,
    ImageSubtractionStage,
    SubtractionRequest,
    available_subtractors,
    create_subtractor,
)
from paloma.core.subtractor import Subtractor
from paloma.image_subtraction import DefaultSubtractor


def test_default_subtractor_registered():
    assert "default" in available_subtractors()
    s = create_subtractor("default")
    assert isinstance(s, DefaultSubtractor)
    assert isinstance(s, Subtractor)


def test_stage_from_config():
    stage = ImageSubtractionStage.from_config(
        ImageSubtractionConfig(subtractor="default", params={"blknum": 5})
    )
    assert stage.subtractor.name == "default"
