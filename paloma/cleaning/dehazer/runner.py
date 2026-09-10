"""Dehazing orchestration: ``dehaze`` entry point + fluent facade.

Handles GPU resolution, file discovery, batching, and output markers, then
runs :func:`~paloma.cleaning.dehazer.workflow.build_chain` per batch.
"""

from __future__ import annotations

import glob
import math
import os
import time
from dataclasses import dataclass, field
from typing import List

from paloma.core.log import banner, configure_warnings, info, warn
from .core import detect_gpu, is_gpu_free
from .io import DEHAZED_PREFIX, get_fits_files, load_fits_directory
from .workflow import (
    Chain,
    EstimateAirlight,
    MoveCubeToDevice,
    RecoverAndSave,
    SmoothAirlight,
    Transmission,
    WorkflowContext,
    build_chain,
)


@dataclass
class DehazeResult:
    """Outcome of a dehazing run."""

    label: str
    input_dir: str
    output_dir: str
    outputs: List[str] = field(default_factory=list)

    @property
    def num_outputs(self) -> int:
        return len(self.outputs)

    @classmethod
    def collect(cls, label: str, input_dir: str, output_dir: str) -> "DehazeResult":
        pattern = os.path.join(os.path.abspath(output_dir), f"{DEHAZED_PREFIX}*.fits")
        return cls(
            label=label,
            input_dir=os.path.abspath(input_dir),
            output_dir=os.path.abspath(output_dir),
            outputs=sorted(glob.glob(pattern)),
        )


def _resolve_gpu(cfg):
    """Return True only when GPU is opted in, present, and idle enough."""
    if not cfg.use_gpu:
        return False
    if not detect_gpu():
        warn("GPU: no CUDA device found, running on CPU")
        return False
    if not is_gpu_free():
        warn("GPU: device is busy, running on CPU")
        return False
    info("GPU: CUDA device is available and free — using CuPy acceleration")
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
    info(f"Wrote path hint: {marker}")


def dehaze(input_dir, output_dir, cfg):
    """Spatio-temporal (3-D) dehazing over a directory of TESS FITS frames."""
    configure_warnings()
    os.makedirs(output_dir, exist_ok=True)
    pipeline_start = time.time()
    out_abs = os.path.abspath(output_dir)
    in_abs = os.path.abspath(input_dir)

    extra = []
    extra.append(
        f"Config: patch={cfg.patch_size}, var_thr={cfg.variance_threshold}, "
        f"nn_thr={cfg.nn_dist_threshold}"
    )
    extra.append(
        f"Temporal: sigma={cfg.sigma_temporal}, "
        f"guided_r={cfg.guided_filter_radius}, "
        f"guided_eps={cfg.guided_filter_eps}"
    )
    if cfg.batch_size is not None:
        extra.append(f"Batch size: {cfg.batch_size} frames per batch")
    banner(
        "Cleaning (3-D Spatio-Temporal Dehazing)",
        f"Input:  {in_abs}",
        f"Output: {out_abs}",
        *extra,
    )
    use_gpu = _resolve_gpu(cfg)

    all_files = _get_fits_files(input_dir, cfg.num_frames)
    info(f"Found {len(all_files)} frames to process.")

    chain = build_chain()
    for batch_idx, num_batches, batch_files in _iter_batches(all_files, cfg.batch_size):
        batch_label = (
            f"Batch {batch_idx + 1}/{num_batches}" if num_batches > 1 else ""
        )
        if batch_label:
            banner(f"{batch_label}  ({len(batch_files)} frames)")
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
    info(f"Cleaning complete in {total:.1f}s.")
    info(f"FITS written under {out_abs}")
    _write_output_location_marker(output_dir, input_dir, "dehaze")
    return DehazeResult.collect("default", input_dir, output_dir)


class DehazePipeline:
    """Fluent, method-chaining facade over the (spatio-temporal) stage chain."""

    def __init__(self, cfg, use_gpu=False, batch_label=""):
        self.ctx = WorkflowContext(cfg=cfg, use_gpu=use_gpu, label=batch_label)

    def load(self, cube, metadata):
        self.ctx.cube = cube
        self.ctx.metadata = metadata
        MoveCubeToDevice().run(self.ctx)
        return self

    def estimate_airlight(self):
        EstimateAirlight().run(self.ctx)
        return self

    def smooth_airlight(self):
        SmoothAirlight().run(self.ctx)
        return self

    def transmission(self):
        Transmission().run(self.ctx)
        return self

    def recover_and_save(self, output_dir):
        self.ctx.output_dir = output_dir
        RecoverAndSave().run(self.ctx)
        return self

    def run(self, output_dir):
        """Run Steps 1-4 in order on the already-loaded batch."""
        self.ctx.output_dir = output_dir
        chain = Chain([
            EstimateAirlight(),
            SmoothAirlight(),
            Transmission(),
            RecoverAndSave(),
        ])
        chain.run(self.ctx)
        return self
