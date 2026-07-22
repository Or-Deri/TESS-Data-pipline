"""Command-line interface: ``dehaze``, ``simulate``, ``validate``.

See ``docs/workflow/01-setup.md`` for the full flag contract.
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
    dehaze.add_argument("--input-dir", required=True)
    dehaze.add_argument("--output-dir", default=None)
    dehaze.add_argument("--output-base", default=None)
    dehaze.add_argument("--structured-layout", action="store_true")
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
    """Override a default DehazeConfig with any explicitly-provided flags."""
    cfg = DehazeConfig()
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
    cfg = _build_config(args)

    if args.structured_layout:
        if not args.output_base:
            raise SystemExit("--output-base is required with --structured-layout")
        files = _get_fits_files(args.input_dir, cfg.num_frames)
        output_dir = structured_dehaze_output_dir(
            args.output_base, cfg, args.input_dir, files=files
        )
    else:
        if not args.output_dir:
            raise SystemExit("--output-dir is required unless --structured-layout")
        output_dir = args.output_dir

    context = DehazingContext.default()
    context.execute(args.input_dir, output_dir, cfg)
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
