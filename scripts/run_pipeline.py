#!/usr/bin/env python3
"""Run the Paloma pipeline (Cleaning → Image Subtraction) from ``.env``.

Usage::

    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --input-dir path/to/fits --output-dir results
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running without an editable install when cwd is the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from paloma.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
