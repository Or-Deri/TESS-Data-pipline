"""CLI for the image-subtraction engine.

Paths and engine params default from ``.env`` (``PALOMA_*``); CLI flags win.
"""

from __future__ import annotations

import argparse

from .config import SubtractionConfig
from .pipeline import subtract


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paloma.image_subtraction")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("subtract", help="Run optimal image subtraction")
    run.add_argument(
        "--input-dir",
        default=None,
        help="FITS input dir (default: PALOMA_INPUT_DIR)",
    )
    run.add_argument(
        "--output-dir",
        default=None,
        help="Output dir (default: PALOMA_OUTPUT_DIR)",
    )
    run.add_argument("--blknum", type=int, default=None)
    run.add_argument("--num-iterations", type=int, default=None)
    run.add_argument("--nr-stars", type=int, default=None)
    run.add_argument("--random-seed", type=int, default=None)
    run.add_argument("--num-frames", type=int, default=None)
    run.add_argument("--no-dquality-filter", action="store_true")
    return parser


def _build_config(args) -> SubtractionConfig:
    """Start from ``.env`` / env defaults, then apply explicit CLI flags."""
    from paloma.env import load_env

    load_env()
    cfg = SubtractionConfig.from_env(load_dotenv=False)
    for key in ("blknum", "num_iterations", "nr_stars", "random_seed", "num_frames"):
        val = getattr(args, key, None)
        if val is not None:
            setattr(cfg, key, val)
    if getattr(args, "no_dquality_filter", False):
        cfg.apply_data_quality_filter = False
    return cfg


def main(argv=None) -> None:
    from paloma.env import paths_from_env

    args = build_parser().parse_args(argv)
    if args.command == "subtract":
        paths = paths_from_env()
        input_dir = args.input_dir or paths.input_dir
        output_dir = args.output_dir or paths.output_dir
        if not input_dir:
            raise SystemExit("--input-dir or PALOMA_INPUT_DIR is required")
        if not output_dir:
            raise SystemExit("--output-dir or PALOMA_OUTPUT_DIR is required")
        subtract(input_dir, output_dir, _build_config(args))


if __name__ == "__main__":
    main()
