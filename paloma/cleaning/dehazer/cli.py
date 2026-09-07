"""Command-line interface: ``dehaze``, ``simulate``, ``validate``.

See ``docs/workflow/01-setup.md`` for the full flag contract.
Paths and engine params default from ``.env`` (``PALOMA_*``); CLI flags win.
"""

import argparse

from .config import DehazeConfig
from .io import structured_dehaze_output_dir
from .pipeline import _get_fits_files
from .strategies import DehazingContext


def _add_common_args(parser):
    parser.add_argument("--patch-size", type=int, default=None)
    parser.add_argument("--variance-threshold", type=float, default=None)
    parser.add_argument("--nn-dist-threshold", type=float, default=None)
    parser.add_argument("--sigma-temporal", type=float, default=None)
    parser.add_argument("--t-min-clip", type=float, default=None)
    parser.add_argument("--guided-filter-radius", type=int, default=None)
    parser.add_argument("--guided-filter-eps", type=float, default=None)
    parser.add_argument("--num-frames", type=int, default=None)
    parser.add_argument("--max-patches", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--gpu", action="store_true")


def build_parser():
    parser = argparse.ArgumentParser(prog="paloma.cleaning.dehazer")
    sub = parser.add_subparsers(dest="command", required=True)

    dehaze = sub.add_parser("dehaze", help="Run the dehazing pipeline")
    dehaze.add_argument(
        "--input-dir",
        default=None,
        help="FITS input dir (default: PALOMA_INPUT_DIR)",
    )
    dehaze.add_argument(
        "--output-dir",
        default=None,
        help="Output dir (default: PALOMA_OUTPUT_DIR)",
    )
    dehaze.add_argument(
        "--output-base",
        default=None,
        help="Structured-layout base (default: PALOMA_OUTPUT_BASE)",
    )
    dehaze.add_argument(
        "--structured-layout",
        action="store_true",
        help="Use structured output dirs (or PALOMA_STRUCTURED_LAYOUT=true)",
    )
    dehaze.add_argument(
        "--strategy",
        default=None,
        help="Dehazer strategy label (default: PALOMA_DEHAZE_STRATEGY)",
    )
    _add_common_args(dehaze)

    sim = sub.add_parser("simulate", help="Generate a synthetic sequence")
    sim.add_argument("--output-dir", required=True)
    sim.add_argument("--clean-fits", required=True)
    sim.add_argument("--type", choices=["cloud", "null"], default="cloud")
    sim.add_argument("--num-frames", type=int, default=10)

    val = sub.add_parser("validate", help="Score a dehazed synthetic sequence")
    val.add_argument("--sim-dir", required=True)
    val.add_argument("--output-dir", required=True)
    _add_common_args(val)

    return parser


def _build_config(args):
    """Start from ``.env`` / env defaults, then apply explicit CLI flags."""
    from paloma.env import load_env

    load_env()
    cfg = DehazeConfig.from_env(load_dotenv=False)
    overrides = {
        "patch_size": getattr(args, "patch_size", None),
        "variance_threshold": getattr(args, "variance_threshold", None),
        "nn_dist_threshold": getattr(args, "nn_dist_threshold", None),
        "sigma_temporal": getattr(args, "sigma_temporal", None),
        "t_min_clip": getattr(args, "t_min_clip", None),
        "guided_filter_radius": getattr(args, "guided_filter_radius", None),
        "guided_filter_eps": getattr(args, "guided_filter_eps", None),
        "num_frames": getattr(args, "num_frames", None),
        "max_patches": getattr(args, "max_patches", None),
        "batch_size": getattr(args, "batch_size", None),
    }
    for key, value in overrides.items():
        if value is not None:
            setattr(cfg, key, value)
    if getattr(args, "gpu", False):
        cfg.use_gpu = True
    return cfg


def _handle_dehaze(args):
    from paloma.env import env_str, paths_from_env

    cfg = _build_config(args)
    paths = paths_from_env(load_dotenv=False)

    input_dir = args.input_dir or paths.input_dir
    if not input_dir:
        raise SystemExit("--input-dir or PALOMA_INPUT_DIR is required")

    structured = bool(args.structured_layout) or paths.structured_layout
    output_base = args.output_base or paths.output_base
    output_dir = args.output_dir or paths.output_dir

    if structured:
        if not output_base:
            raise SystemExit(
                "--output-base or PALOMA_OUTPUT_BASE is required with structured layout"
            )
        files = _get_fits_files(input_dir, cfg.num_frames)
        output_dir = structured_dehaze_output_dir(
            output_base, cfg, input_dir, files=files
        )
    elif not output_dir:
        raise SystemExit("--output-dir or PALOMA_OUTPUT_DIR is required")

    strategy = args.strategy or env_str("PALOMA_DEHAZE_STRATEGY", "default") or "default"
    context = DehazingContext.from_label(strategy)
    context.execute(input_dir, output_dir, cfg)
    return 0


def _handle_simulate(args):
    from .evaluation import run_simulation

    run_simulation(args.output_dir, args.clean_fits, args.type, args.num_frames)
    return 0


def _handle_validate(args):
    from .evaluation import run_validation

    cfg = _build_config(args)
    run_validation(args.sim_dir, args.output_dir, cfg)
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "dehaze":
        return _handle_dehaze(args)
    if args.command == "simulate":
        return _handle_simulate(args)
    if args.command == "validate":
        return _handle_validate(args)

    parser.error(f"Unknown command {args.command!r}")
    return 1
