#!/usr/bin/env python3
"""Generate ground-truth fixtures for the image-subtraction engine.

Runs the reference implementation from the sibling ``image-subtraction`` repo on
the 5 raw TESS FFIs in ``tests/data/cleaning/groundtruth/raw/``, with
``random.seed(0)`` for reproducible kernel-star selection.

Prerequisites:
  - FITS_tools (hcongrid): pip install git+https://github.com/keflavich/FITS_tools.git
  - Compiled C binary at ``build/a.out`` (see README in groundtruth folder)
  - photutils, lightkurve, astropy, numpy, scipy

Usage (from repo root)::

    source .venv/bin/activate
    python scripts/generate_image_subtraction_groundtruth.py
"""

from __future__ import annotations

import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF_REPO = ROOT.parent / "image-subtraction"
RAW_SRC = ROOT / "tests" / "data" / "cleaning" / "groundtruth" / "raw"
GT_ROOT = ROOT / "tests" / "data" / "image_subtraction" / "groundtruth"
CODE_DIR = ROOT / "build" / "code_dir"
C_BINARY = ROOT / "build" / "a.out"
SUBTRACTED_PREFIX = "subtracted__"


def _setup_paths() -> None:
    if not REF_REPO.is_dir():
        sys.exit(f"Reference repo not found: {REF_REPO}")
    if str(REF_REPO) not in sys.path:
        sys.path.insert(0, str(REF_REPO))
    if not RAW_SRC.is_dir():
        sys.exit(f"Raw fixtures not found: {RAW_SRC}")
    if not C_BINARY.is_file():
        sys.exit(
            f"C binary not found: {C_BINARY}\n"
            "Compile with:\n"
            "  gcc ../image-subtraction/TESS/oisdifference.c "
            "-Ibuild/cfitsio/install/include -Lbuild/cfitsio/install/lib "
            "-lcfitsio -lm -o build/a.out"
        )


def _patch_file_filter() -> None:
    """Accept test FFIs that fail the default DQUALITY mask (same raw set as dehazer)."""
    import src.core_science as cs  # noqa: WPS433

    _orig = cs.fileFilter

    def _relaxed_filter(file_list, check_header=True, data_quality_mask=0, **kwargs):
        return _orig(file_list, check_header=check_header, data_quality_mask=data_quality_mask, **kwargs)

    cs.fileFilter = _relaxed_filter


def _patch_random_seed(seed: int = 0) -> None:
    """Pin RNG before reference star selection for reproducible groundtruth."""
    random.seed(seed)

    import src.core_science as cs  # noqa: WPS433 — reference repo module

    _orig = cs.refStars

    def _seeded_ref_stars(*args, **kwargs):
        random.seed(seed)
        return _orig(*args, **kwargs)

    cs.refStars = _seeded_ref_stars

    import src.subtraction as sub  # noqa: WPS433

    sub.refStars = _seeded_ref_stars


def _prepare_workspace(parent: Path) -> None:
    """Lay out raw FFIs in the reference pipeline folder structure."""
    raw_dir = parent / "s0003-c2-ccd1" / "00_raw_ffi"
    if raw_dir.exists():
        shutil.rmtree(parent / "s0003-c2-ccd1")
    raw_dir.mkdir(parents=True)
    for src in sorted(RAW_SRC.glob("*.fits")):
        shutil.copy2(src, raw_dir / src.name)

    CODE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(C_BINARY, CODE_DIR / "a.out")


def _capture_outputs(parent: Path, expected: Path) -> None:
    """Copy reference residuals (+ optional sources CSV) into expected/."""
    ccd = parent / "s0003-c2-ccd1"
    residuals_src = ccd / "04_residual_img"
    sources_src = ccd / "05_sources" / "found_sources.csv"

    expected_residuals = expected / "residuals"
    expected_residuals.mkdir(parents=True, exist_ok=True)

    for fits in sorted(residuals_src.glob("*.fits")):
        dest = expected_residuals / f"{SUBTRACTED_PREFIX}{fits.name}"
        shutil.copy2(fits, dest)

    if sources_src.is_file():
        shutil.copy2(sources_src, expected / "found_sources.csv")


def main() -> None:
    _setup_paths()
    _patch_file_filter()
    _patch_random_seed(0)

    from src.pipeline import process_sector_pipeline  # noqa: WPS433

    work = GT_ROOT / "_work"
    expected = GT_ROOT / "expected"
    raw_link = GT_ROOT / "raw"

    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    if expected.exists():
        shutil.rmtree(expected)
    expected.mkdir(parents=True)

    # Symlink raw fixtures for documentation (portable relative path)
    if raw_link.exists() or raw_link.is_symlink():
        raw_link.unlink()
    raw_link.symlink_to(Path("../../cleaning/groundtruth/raw"))

    _prepare_workspace(work)

    print("Running reference image-subtraction pipeline (blknum=5, seed=0)...")
    process_sector_pipeline(
        sector=3,
        camera=2,
        ccd=1,
        parent_folder=str(work),
        code_dir=str(CODE_DIR),
        blknum=5,
        num_iterations=2,
        nr_stars=500,
        kernel=2,
        stamp=3,
        order=0,
        aperture_rad=3,
        threshold_source_detection=50.0,
        full_width_half_maximum=1.5,
        edge_cutoff=3,
        match_radius=3,
    )

    _capture_outputs(work, expected)

    readme = GT_ROOT / "README.md"
    readme.write_text(
        f"""# Ground-truth fixtures — image subtraction

Verification set for the OIS pipeline (TESS sector s0003-2-1, 5 FFIs).

| Path | Contents |
|---|---|
| [`raw/`](raw/) | Symlink to `tests/data/cleaning/groundtruth/raw/` (5 undehazed FFIs) |
| [`expected/residuals/`](expected/residuals/) | Reference `subtracted__*.fits` (slow pytest pin) |
| [`expected/found_sources.csv`](expected/found_sources.csv) | Cross-matched source catalog |

## Reproduce

```bash
source .venv/bin/activate
python scripts/generate_image_subtraction_groundtruth.py
```

Generated with ``random.seed(0)``, ``blknum=5``, ``num_iterations=2``.
""",
        encoding="utf-8",
    )

    n_res = len(list((expected / "residuals").glob("*.fits")))
    print(f"Done. {n_res} residuals -> {GT_ROOT}")


if __name__ == "__main__":
    main()
