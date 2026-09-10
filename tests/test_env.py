"""Ensure every ``.env.example`` key is wired into code."""

from __future__ import annotations

import re
from dataclasses import fields
from pathlib import Path

from paloma import CleaningConfig, ImageSubtractionConfig, PipelineConfig, paths_from_env
from paloma.cleaning.dehazer import DehazeConfig
from paloma.env import ENV_KEYS, REPO_ROOT, load_env
from paloma.image_subtraction import SubtractionConfig

EXAMPLE = REPO_ROOT / ".env.example"


def _keys_in_example() -> set[str]:
    keys = set()
    for line in EXAMPLE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Z0-9_]+)=", line)
        if match:
            keys.add(match.group(1))
    return keys


def test_env_example_matches_env_keys_catalog():
    assert EXAMPLE.is_file()
    example_keys = _keys_in_example()
    assert example_keys == set(ENV_KEYS), (
        f"missing in ENV_KEYS: {sorted(example_keys - set(ENV_KEYS))}\n"
        f"extra in ENV_KEYS: {sorted(set(ENV_KEYS) - example_keys)}"
    )


def test_from_env_loads_all_engine_params():
    """Every DehazeConfig / SubtractionConfig field is populated from env."""
    load_env(EXAMPLE, override=True)

    dehaze = DehazeConfig.from_env(load_dotenv=False)
    for field in fields(DehazeConfig):
        assert hasattr(dehaze, field.name)

    sub = SubtractionConfig.from_env(load_dotenv=False)
    for field in fields(SubtractionConfig):
        assert hasattr(sub, field.name)
    assert sub.code_dir is not None
    assert Path(sub.code_dir).is_absolute()

    paths = paths_from_env(load_dotenv=False)
    assert paths.input_dir is not None
    assert paths.output_dir is not None
    assert paths.structured_layout is False

    cleaning = CleaningConfig.from_env(load_dotenv=False)
    assert cleaning.cleaner == "dehazer"
    assert cleaning.params["strategy"] == "default"
    assert cleaning.params["num_frames"] == dehaze.num_frames

    img = ImageSubtractionConfig.from_env(load_dotenv=False)
    assert img.subtractor == "default"
    assert img.params["blknum"] == sub.blknum

    pipeline = PipelineConfig.from_env(load_dotenv=False)
    assert pipeline.cleaning.cleaner == cleaning.cleaner
    assert pipeline.subtraction.subtractor == img.subtractor
    assert pipeline.input_dir == paths.input_dir
    assert pipeline.output_dir == paths.output_dir
    assert pipeline.resolve_cleaned_dir().endswith("cleaned")
    assert pipeline.resolve_subtracted_dir().endswith("subtracted")
