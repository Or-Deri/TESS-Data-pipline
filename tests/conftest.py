"""Root pytest configuration shared by all package test suites."""

import sys
from pathlib import Path

# Make the repo root importable so ``import paloma`` resolves regardless of
# pytest's rootdir handling.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
