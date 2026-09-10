"""Load Paloma parameters from environment / ``.env`` files.

Prefixed variables (``PALOMA_*``) override dataclass defaults. Call
:func:`load_env` once at process start (CLI does this automatically), or use
:meth:`DehazeConfig.from_env` / :meth:`SubtractionConfig.from_env` /
:meth:`~paloma.config.CleaningConfig.from_env`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_LOADED = False

# Repo root (parent of ``paloma/``). Relative ``.env`` paths resolve here.
REPO_ROOT = Path(__file__).resolve().parents[1]

# Every ``PALOMA_*`` key that appears in ``.env.example`` / is read by code.
# Keep in sync with ``.env.example`` (guarded by tests/test_env.py).
ENV_KEYS = frozenset(
    {
        # I/O
        "PALOMA_INPUT_DIR",
        "PALOMA_OUTPUT_DIR",
        "PALOMA_OUTPUT_BASE",
        "PALOMA_STRUCTURED_LAYOUT",
        "PALOMA_CLEANED_DIR",
        "PALOMA_SUBTRACTED_DIR",
        # Cleaning stage
        "PALOMA_CLEANER",
        "PALOMA_DEHAZE_STRATEGY",
        "PALOMA_DEHAZE_NUM_FRAMES",
        "PALOMA_DEHAZE_BATCH_SIZE",
        "PALOMA_DEHAZE_FITS_EXTENSION",
        "PALOMA_DEHAZE_CROP_BOTTOM",
        "PALOMA_DEHAZE_CROP_SIDES",
        "PALOMA_DEHAZE_PATCH_SIZE",
        "PALOMA_DEHAZE_VARIANCE_THRESHOLD",
        "PALOMA_DEHAZE_NN_DIST_THRESHOLD",
        "PALOMA_DEHAZE_MAX_PATCHES",
        "PALOMA_DEHAZE_NUM_ITERATIONS",
        "PALOMA_DEHAZE_SIGMA_TEMPORAL",
        "PALOMA_DEHAZE_T_MIN_CLIP",
        "PALOMA_DEHAZE_GUIDED_FILTER_RADIUS",
        "PALOMA_DEHAZE_GUIDED_FILTER_EPS",
        "PALOMA_DEHAZE_USE_GPU",
        # Image subtraction stage
        "PALOMA_SUBTRACTOR",
        "PALOMA_SUBTRACTION_NUM_FRAMES",
        "PALOMA_SUBTRACTION_FITS_EXTENSION",
        "PALOMA_SUBTRACTION_CUTOUT_CENTER",
        "PALOMA_SUBTRACTION_CUTOUT_SIZE",
        "PALOMA_SUBTRACTION_CRPIX1",
        "PALOMA_SUBTRACTION_APPLY_DATA_QUALITY_FILTER",
        "PALOMA_SUBTRACTION_DATA_QUALITY_MASK",
        "PALOMA_SUBTRACTION_KERNEL",
        "PALOMA_SUBTRACTION_STAMP",
        "PALOMA_SUBTRACTION_ORDER",
        "PALOMA_SUBTRACTION_NR_STARS",
        "PALOMA_SUBTRACTION_BLKNUM",
        "PALOMA_SUBTRACTION_NUM_ITERATIONS",
        "PALOMA_SUBTRACTION_RANDOM_SEED",
        "PALOMA_SUBTRACTION_THRESHOLD_SOURCE_DETECTION",
        "PALOMA_SUBTRACTION_FWHM",
        "PALOMA_SUBTRACTION_EDGE_CUTOFF",
        "PALOMA_SUBTRACTION_MATCH_RADIUS",
        "PALOMA_SUBTRACTION_APERTURE_RAD",
        "PALOMA_SUBTRACTION_SOURCE_FILTER_THRESHOLD",
        "PALOMA_SUBTRACTION_USE_C_BACKEND",
        "PALOMA_SUBTRACTION_CODE_DIR",
    }
)


def load_env(dotenv_path: Optional[str | Path] = None, *, override: bool = False) -> bool:
    """Load a ``.env`` file into ``os.environ`` if ``python-dotenv`` is installed.

    Searches the repo root (parent of ``paloma/``) for ``.env`` when
    ``dotenv_path`` is omitted. Returns whether a file was loaded.
    """
    global _LOADED
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False

    if dotenv_path is None:
        dotenv_path = REPO_ROOT / ".env"
    path = Path(dotenv_path)
    if not path.is_file():
        return False
    load_dotenv(path, override=override)
    _LOADED = True
    return True


def env_str(key: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def env_bool(key: str, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: Optional[int] = None) -> Optional[int]:
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return int(value.strip(), 0)  # base 0: accepts 0b… / 0x…


def env_float(key: str, default: Optional[float] = None) -> Optional[float]:
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return float(value.strip())


def env_int_pair(key: str, default: tuple[int, int]) -> tuple[int, int]:
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 2:
        raise ValueError(f"{key} must be 'x,y' (got {value!r})")
    return int(parts[0]), int(parts[1])


def resolve_path(value: Optional[str]) -> Optional[str]:
    """Resolve a possibly-relative path against :data:`REPO_ROOT`."""
    if value is None or value.strip() == "":
        return None
    path = Path(value.strip()).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return str(path.resolve())


@dataclass(frozen=True)
class IOPaths:
    """Filesystem paths shared across stages (from ``PALOMA_*`` I/O keys)."""

    input_dir: Optional[str] = None
    output_dir: Optional[str] = None
    output_base: Optional[str] = None
    structured_layout: bool = False


def paths_from_env(*, load_dotenv: bool = True) -> IOPaths:
    """Read ``PALOMA_INPUT_DIR`` / ``OUTPUT_*`` / ``STRUCTURED_LAYOUT``."""
    if load_dotenv:
        load_env()
    return IOPaths(
        input_dir=resolve_path(env_str("PALOMA_INPUT_DIR")),
        output_dir=resolve_path(env_str("PALOMA_OUTPUT_DIR")),
        output_base=resolve_path(env_str("PALOMA_OUTPUT_BASE")),
        structured_layout=env_bool("PALOMA_STRUCTURED_LAYOUT", False),
    )
