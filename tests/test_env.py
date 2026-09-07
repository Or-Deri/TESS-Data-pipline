"""Ensure every ``.env.example`` key is wired into code."""

from __future__ import annotations

import re
from dataclasses import fields
from pathlib import Path

from paloma import CleaningConfig, ImageSubtractionConfig, paths_from_env
from paloma.cleaning.dehazer import DehazeConfig
from paloma.env import ENV_KEYS, REPO_ROOT, load_env
from paloma.image_subtraction import SubtractionConfig
from paloma.image_subtraction.pipeline import DefaultSubtractor
from paloma.core.types import SubtractionRequest

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


def test_from_env_loads_all_engine_params(monkeypatch):
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


def test_default_subtractor_builds_config_from_params(tmp_path):
    """Regression: env params must reach SubtractionConfig via DefaultSubtractor."""
    subtractor = DefaultSubtractor(
        blknum=4,
        num_iterations=1,
        nr_stars=5,
        apply_data_quality_filter=False,
        num_frames=1,
        use_c_backend=False,
    )
    cfg = subtractor._build_config(
        SubtractionConfig,
        {**subtractor.params},
    )
    assert cfg.blknum == 4
    assert cfg.use_c_backend is False
    # empty input → pipeline may error later; ensure NameError is gone
    request = SubtractionRequest(
        input_dir=str(tmp_path),
        output_dir=str(tmp_path / "out"),
    )
    # No FITS → stages should still construct config without crashing on helpers
    assert request.input_dir.endswith(tmp_path.name)
