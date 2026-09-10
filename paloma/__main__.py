"""CLI entry: ``python -m paloma`` runs the full pipeline from ``.env``."""

from __future__ import annotations

import argparse
import sys

from paloma.pipeline import Pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Cleaning → Image Subtraction using parameters from .env",
    )
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Override PALOMA_INPUT_DIR",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override PALOMA_OUTPUT_DIR (cleaned/ and subtracted/ live under this)",
    )
    parser.add_argument(
        "--cleaned-dir",
        default=None,
        help="Override PALOMA_CLEANED_DIR",
    )
    parser.add_argument(
        "--subtracted-dir",
        default=None,
        help="Override PALOMA_SUBTRACTED_DIR",
    )
    args = parser.parse_args(argv)

    pipeline = Pipeline.from_env()
    result = pipeline.run(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        cleaned_dir=args.cleaned_dir,
        subtracted_dir=args.subtracted_dir,
    )

    if result.cleaning is None:
        print("Cleaning produced no outputs; pipeline stopped.", file=sys.stderr)
        return 1

    print(
        f"Cleaning: {result.cleaning.num_outputs} frames → {result.cleaning.output_dir}"
    )

    if result.subtraction is None:
        print("Image subtraction produced no outputs.", file=sys.stderr)
        return 1

    sub = result.subtraction
    print(f"Subtraction: {sub.num_outputs} residuals → {sub.output_dir}")
    if sub.sources_csv:
        print(f"Sources: {sub.sources_csv}")
    if sub.lightcurve_dir:
        print(f"Light curves: {sub.lightcurve_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
