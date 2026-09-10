"""Compact stdout helpers for pipeline progress."""

from __future__ import annotations

import warnings


def configure_warnings() -> None:
    """Silence known-noisy third-party warnings that drown pipeline output."""
    warnings.filterwarnings(
        "ignore",
        message=r"Warning: the tpfmodel submodule is not available.*",
        category=UserWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message=r"The column name 'xcentroid' was deprecated.*",
    )
    warnings.filterwarnings(
        "ignore",
        message=r"The column name 'ycentroid' was deprecated.*",
    )


def banner(title: str, *lines: str) -> None:
    print()
    print("=" * 60)
    print(f"  {title}")
    for line in lines:
        if line:
            print(f"  {line}")
    print("=" * 60)


def step(n: int, total: int, label: str, prefix: str = "") -> None:
    print(f"\n{prefix}--- Step {n}/{total}: {label} ---")


def info(msg: str, prefix: str = "") -> None:
    print(f"{prefix}  {msg}")


def warn(msg: str, prefix: str = "") -> None:
    print(f"{prefix}  WARNING: {msg}")


def item(i: int, n: int, msg: str, prefix: str = "") -> None:
    print(f"{prefix}  [{i}/{n}] {msg}")
