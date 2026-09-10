"""Concrete dehazing stages, composed into a chain by :mod:`tess_dehazing.pipeline`.

Each stage maps to one step of the dehazing chain
(``README.md``). The numeric behaviour is unchanged —
these classes package the algorithm into composable
:class:`~paloma.core.chain.Stage` units.

3-D batch chain (one globally-normalized cube)::

    MoveCubeToDevice()
        >> EstimateAirlight()   # Step 1 - 03-estimate-airlight
        >> SmoothAirlight()     # Step 2 - 04-smooth-airlight
        >> Transmission()       # Step 3 - 05-transmission
        >> RecoverAndSave()     # Step 4 - 06-recover-save
"""

from __future__ import annotations

import os
import time

import numpy as np
from scipy.ndimage import gaussian_filter1d

from ..core import (
    estimate_airlight,
    gaussian_filter_temporal,
    get_array_module,
    extract_patches,
    find_pairs,
    recover_image,
    recover_transmission_map,
    to_cpu,
    to_gpu,
)
from ..io import DEHAZED_PREFIX, denormalize, save_fits
from paloma.core.chain import Stage
from paloma.core.log import info, item, step


class MoveCubeToDevice(Stage):
    """Bind the loaded cube to the compute device and pick its array module."""

    name = "move_cube_to_device"

    def apply(self, ctx):
        cube = ctx.cube
        if cube is None:
            raise RuntimeError("ctx.cube must be set (load a batch) before this stage")
        n, h, w = cube.shape
        info(f"Data cube: {n} frames x {h}x{w}", prefix=ctx.prefix)
        if ctx.use_gpu:
            cube = to_gpu(cube)
        ctx.cube = cube
        ctx.xp = get_array_module(cube)
        return ctx


class EstimateAirlight(Stage):
    """Step 1: per-frame raw airlight from patch-recurrence pairs."""

    name = "estimate_airlight"
    requires = ("move_cube_to_device",)

    def apply(self, ctx):
        cfg = ctx.cfg
        cube = ctx.cube
        n = cube.shape[0]
        step_start = time.time()
        step(1, 4, "Estimating per-frame airlight", prefix=ctx.prefix)

        raw_airlights = []
        for i in range(n):
            image = cube[i]
            original, descriptors = extract_patches(
                image, cfg.patch_size, cfg.variance_threshold, cfg.max_patches,
            )
            pairs = find_pairs(original, descriptors, cfg.nn_dist_threshold)
            a = estimate_airlight(pairs, cfg.num_iterations)
            raw_airlights.append(a)
            item(
                i + 1,
                n,
                f"{ctx.metadata[i]['filename']}  "
                f"A={a:.4f}  patches={int(original.shape[0])}  pairs={len(pairs)}",
                prefix=ctx.prefix,
            )

        ctx.raw_airlights = raw_airlights
        info(f"Raw airlights: {[round(a, 4) for a in raw_airlights]}", prefix=ctx.prefix)
        info(f"Step 1 completed in {time.time() - step_start:.1f}s", prefix=ctx.prefix)
        return ctx


class SmoothAirlight(Stage):
    """Step 2: temporal Gaussian smoothing of the airlight series (CPU)."""

    name = "smooth_airlight"
    requires = ("estimate_airlight",)

    def apply(self, ctx):
        cfg = ctx.cfg
        step_start = time.time()
        step(
            2, 4, f"Smoothing airlight temporally (sigma={cfg.sigma_temporal})",
            prefix=ctx.prefix,
        )
        airlights = gaussian_filter1d(
            np.array(ctx.raw_airlights), sigma=cfg.sigma_temporal, axis=0,
        )
        ctx.airlights = airlights
        delta = np.abs(np.array(ctx.raw_airlights) - airlights)
        info(f"Smoothed A: {[round(float(a), 4) for a in airlights]}", prefix=ctx.prefix)
        info(f"Max smoothing delta: {delta.max():.6f}", prefix=ctx.prefix)
        info(f"Step 2 completed in {time.time() - step_start:.1f}s", prefix=ctx.prefix)
        return ctx


class Transmission(Stage):
    """Step 3: per-frame transmission from smoothed A, then temporal smooth."""

    name = "transmission"
    requires = ("smooth_airlight",)

    def apply(self, ctx):
        cfg = ctx.cfg
        cube = ctx.cube
        xp = ctx.xp
        n = cube.shape[0]
        step_start = time.time()
        step(3, 4, "Computing and smoothing transmission maps", prefix=ctx.prefix)

        t_cube = xp.zeros_like(cube)
        for i in range(n):
            t_cube[i] = recover_transmission_map(
                cube[i],
                ctx.airlights[i],
                cfg.guided_filter_radius,
                cfg.guided_filter_eps,
                cfg.t_min_clip,
            )
            t = t_cube[i]
            item(
                i + 1,
                n,
                f"A={ctx.airlights[i]:.4f}  "
                f"t=[{float(t.min()):.4f}, {float(t.max()):.4f}]  "
                f"mean={float(t.mean()):.4f}",
                prefix=ctx.prefix,
            )
        info("Applying temporal smoothing to transmission volume ...", prefix=ctx.prefix)
        t_cube = gaussian_filter_temporal(t_cube, sigma=cfg.sigma_temporal)
        ctx.t_cube = t_cube
        info(
            f"Smoothed t-cube: min={float(t_cube.min()):.4f}, "
            f"max={float(t_cube.max()):.4f}, mean={float(t_cube.mean()):.4f}",
            prefix=ctx.prefix,
        )
        info(f"Step 3 completed in {time.time() - step_start:.1f}s", prefix=ctx.prefix)
        return ctx


class RecoverAndSave(Stage):
    """Step 4: recover the latent scene, denormalize, and save each frame."""

    name = "recover_and_save"
    requires = ("transmission",)

    def apply(self, ctx):
        cfg = ctx.cfg
        cube = ctx.cube
        n = cube.shape[0]
        step_start = time.time()
        step(4, 4, "Recovering and saving frames", prefix=ctx.prefix)

        for i in range(n):
            meta = ctx.metadata[i]
            out_name = f"{DEHAZED_PREFIX}{meta['filename']}"
            out_path = os.path.join(ctx.output_dir, out_name)
            if os.path.exists(out_path):
                item(i + 1, n, f"skip (exists): {out_name}", prefix=ctx.prefix)
                continue
            recovered = recover_image(
                cube[i], ctx.airlights[i], ctx.t_cube[i], cfg.t_min_clip,
            )
            result = denormalize(
                to_cpu(recovered), meta["orig_min"], meta["orig_max"],
            )
            save_fits(result, out_path, header=meta.get("header"))
            item(
                i + 1,
                n,
                f"{out_name}  A={ctx.airlights[i]:.4f}  "
                f"range=[{result.min():.2f}, {result.max():.2f}]",
                prefix=ctx.prefix,
            )

        info(f"Step 4 completed in {time.time() - step_start:.1f}s", prefix=ctx.prefix)
        return ctx


def build_chain():
    """Return the canonical dehazing batch chain (Steps 1-4, spatio-temporal)."""
    return (
        MoveCubeToDevice()
        >> EstimateAirlight()
        >> SmoothAirlight()
        >> Transmission()
        >> RecoverAndSave()
    )
