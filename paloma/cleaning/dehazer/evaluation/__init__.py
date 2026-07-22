"""Synthetic-data simulation and quantitative validation (verification path)."""

from .simulation import (
    evaluate_metrics,
    generate_amorphous_cloud,
    generate_null_test,
    run_simulation,
    run_validation,
)

__all__ = [
    "run_simulation",
    "run_validation",
    "evaluate_metrics",
    "generate_amorphous_cloud",
    "generate_null_test",
]
