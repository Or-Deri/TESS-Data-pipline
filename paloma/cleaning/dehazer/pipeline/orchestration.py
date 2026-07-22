"""Top-level orchestration, built on the chain engine.

This module handles the orchestration around the algorithm — GPU resolution,
file discovery, batching, and output markers — and hands each batch to a chain
from :mod:`tess_dehazing.workflow`. The pipeline is spatio-temporal (3-D): each
batch is a globally-normalized cube processed as a whole.

``dehaze`` is the source-of-truth entry point for stage ordering
(``docs/workflow/README.md``). The four steps are intentionally *not* fused; the
chain's ordering guards enforce this at runtime.
"""

import glob
import math
import os
import time

from ..core import detect_gpu, is_gpu_free
from ..io import DEHAZED_PREFIX, get_fits_files, load_fits_directory
from ..workflow import WorkflowContext, build_chain


def _resolve_gpu(cfg):
    """Return True only when GPU is opted in, present, and idle enough."""
    if not cfg.use_gpu:
        return False
    if not detect_gpu():
        print("  GPU: no CUDA device found, running on CPU")
        return False
    if not is_gpu_free():
        print("  GPU: device is busy, running on CPU")
        return False
    print("  GPU: CUDA device is available and free — using CuPy acceleration")
    return True


def _get_fits_files(input_dir, num_frames=None):
    return get_fits_files(input_dir, num_frames)


def _iter_batches(files, batch_size):
    """Yield ``(batch_idx, num_batches, batch_files)`` contiguous groups."""
    if batch_size is None:
        yield 0, 1, files
        return
    num_batches = math.ceil(len(files) / batch_size)
    for b in range(num_batches):
        yield b, num_batches, files[b * batch_size : (b + 1) * batch_size]


def _write_output_location_marker(output_dir, input_dir, label):
    """Write ``OUTPUT_LOCATION.txt`` summarizing the run."""
    abs_out = os.path.abspath(output_dir)
    abs_in = os.path.abspath(input_dir)
    outputs = glob.glob(os.path.join(abs_out, f"{DEHAZED_PREFIX}*.fits"))
    marker = os.path.join(abs_out, "OUTPUT_LOCATION.txt")
    lines = [
        "TESS dehazing pipeline output",
        "",
        "Absolute output folder (FITS are here):",
        f"  {abs_out}",
        "",
        "Input folder:",
        f"  {abs_in}",
        "",
        f"Pipeline: {label}",
        f"dehazed_*.fits files in this folder: {len(outputs)}",
        "",
        "If you used --structured-layout, outputs are NOT next to the input",
        "folder; they are under output_<sector>_GlobalNorm_Subfolders/<params>/",
        "or CCD_<sector>_Results/<params>/ on disk.",
    ]
    with open(marker, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nWrote path hint: {marker}")


def dehaze(input_dir, output_dir, cfg):
    """Spatio-temporal (3-D) dehazing over a directory of TESS FITS frames."""
    os.makedirs(output_dir, exist_ok=True)
    pipeline_start = time.time()
    out_abs = os.path.abspath(output_dir)
    in_abs = os.path.abspath(input_dir)

    print(f"\n{'=' * 60}")
    print("  3-D Spatio-Temporal Dehazing Pipeline")
    print(f"  Input:  {in_abs}")
    print(f"  Output: {out_abs}")
    print(f"  Config: patch={cfg.patch_size}, var_thr={cfg.variance_threshold}, "
          f"nn_thr={cfg.nn_dist_threshold}")
    print(f"  Temporal: sigma={cfg.sigma_temporal}, "
          f"guided_r={cfg.guided_filter_radius}, "
          f"guided_eps={cfg.guided_filter_eps}")
    if cfg.batch_size is not None:
        print(f"  Batch size: {cfg.batch_size} frames per batch")
    use_gpu = _resolve_gpu(cfg)
    print(f"{'=' * 60}")

    all_files = _get_fits_files(input_dir, cfg.num_frames)
    print(f"\nFound {len(all_files)} frames to process.")

    chain = build_chain()
    for batch_idx, num_batches, batch_files in _iter_batches(all_files, cfg.batch_size):
        batch_label = (
            f"Batch {batch_idx + 1}/{num_batches}" if num_batches > 1 else ""
        )
        if batch_label:
            print(f"\n{'=' * 60}")
            print(f"  {batch_label}  ({len(batch_files)} frames)")
            print(f"{'=' * 60}")
        cube, metadata = load_fits_directory(
            input_dir, cfg, files=batch_files
        )
        ctx = WorkflowContext(
            cfg=cfg,
            use_gpu=use_gpu,
            input_dir=input_dir,
            output_dir=output_dir,
            label=batch_label,
            cube=cube,
            metadata=metadata,
        )
        chain.run(ctx)

    total = time.time() - pipeline_start
    print(f"\nPipeline complete in {total:.1f}s.")
    print(f"All FITS written under:\n  {out_abs}\n")
    _write_output_location_marker(output_dir, input_dir, "dehaze")
