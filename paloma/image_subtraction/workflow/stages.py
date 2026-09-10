"""Concrete subtraction workflow stages."""

from __future__ import annotations

import csv
import os
from glob import glob
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from photutils.aperture import CircularAperture

from ..core.background import subtract_background
from ..core.kernel_stars import select_kernel_stars
from ..core.masters import build_final_master, make_master
from ..core.ois import optimal_subtract
from ..core.ois_c import run_c_subtraction
from ..core.photometry import measure_flux_timestamps, propagate_wcs, write_lightcurves
from ..core.preprocess import _has_wcs, get_file_names, preprocess_images
from ..core.sources import (
    cross_match,
    filter_source_list,
    find_sources,
    make_star_list,
    pixel_to_sky,
)
from ..io import SUBTRACTED_PREFIX, background_subtract, save_fits
from paloma.core.chain import Stage
from paloma.core.log import info, item, step, warn



class PreprocessFrames(Stage):
    name = "preprocess_frames"

    def apply(self, ctx):
        cfg = ctx.cfg
        step(1, 5, "Preprocessing raw FFIs", prefix=ctx.prefix)
        files, did_work = preprocess_images(ctx.input_dir, ctx.layout.preprocessed, cfg)
        if not files:
            rejected = os.path.join(ctx.layout.preprocessed, "rejectedFiles.txt")
            hint = (
                f" (see {rejected})"
                if os.path.isfile(rejected)
                else " (check input dir and DQUALITY filter settings)"
            )
            raise RuntimeError(
                f"no FITS frames available after preprocessing{hint}"
            )
        ctx.preprocessed_files = files
        ctx.raw_files = get_file_names(ctx.input_dir, "*.fits")
        if did_work:
            info(f"Preprocessed {len(files)} frames", prefix=ctx.prefix)
        else:
            info(
                f"Using existing preprocessed frames ({len(files)} files)",
                prefix=ctx.prefix,
            )
        return ctx


class BuildReference(Stage):
    name = "build_reference"
    requires = ("preprocess_frames",)

    def apply(self, ctx):
        cfg = ctx.cfg
        step(2, 5, "Building reference master", prefix=ctx.prefix)
        ctx.master_files = make_master(
            ctx.preprocessed_files, ctx.layout.preprocessed, ctx.layout.masters, cfg
        )
        master_names = [os.path.basename(p) for p in ctx.master_files]
        ctx.reference_fits = build_final_master(
            master_names, ctx.layout.masters, ctx.layout.reference, cfg
        )
        ref_img, ref_head = fits.getdata(ctx.reference_fits, header=True)
        positions = find_sources(
            ref_img,
            fwhm=cfg.fwhm,
            threshold=cfg.threshold_source_detection,
            edge_cutoff=cfg.edge_cutoff,
        )
        make_star_list(
            positions,
            ref_img,
            cfg.aperture_rad,
            ctx.layout.reference,
            os.path.basename(ctx.reference_fits),
        )
        info(
            f"Reference {os.path.basename(ctx.reference_fits)}  "
            f"{len(positions)} kernel-star candidates",
            prefix=ctx.prefix,
        )
        return ctx


class OptimalSubtract(Stage):
    name = "optimal_subtract"
    requires = ("build_reference",)

    def apply(self, ctx):
        cfg = ctx.cfg
        step(3, 5, "Optimal image subtraction", prefix=ctx.prefix)
        ref_data, ref_head = fits.getdata(ctx.reference_fits, header=True)
        _, ref_median, _ = sigma_clipped_stats(ref_data, sigma=3.0, maxiters=5)
        ref_bg = ref_data - ref_median

        use_c = bool(cfg.use_c_backend)
        code_dir = cfg.code_dir or str(Path(ctx.output_dir) / "_c_scratch")
        if use_c:
            c_bin = Path(code_dir) / "a.out"
            repo_aout = Path(__file__).resolve().parents[3] / "build" / "a.out"
            if not c_bin.is_file() and not repo_aout.is_file():
                warn(
                    f"C backend a.out not found (looked in {code_dir} and build/); "
                    "using Python OIS",
                    prefix=ctx.prefix,
                )
                use_c = False
            else:
                info("Using C OIS backend", prefix=ctx.prefix)
        else:
            info("Using Python OIS", prefix=ctx.prefix)

        n_frames = len(ctx.preprocessed_files)
        for iteration in range(cfg.num_iterations):
            if cfg.num_iterations > 1:
                info(
                    f"Iteration {iteration + 1}/{cfg.num_iterations}",
                    prefix=ctx.prefix,
                )
            if iteration > 0:
                ctx.master_files = make_master(
                    ctx.preprocessed_files,
                    ctx.layout.preprocessed,
                    ctx.layout.masters,
                    cfg,
                )
                master_names = [os.path.basename(p) for p in ctx.master_files]
                ctx.reference_fits = build_final_master(
                    master_names, ctx.layout.masters, ctx.layout.reference, cfg
                )
                ref_data, ref_head = fits.getdata(ctx.reference_fits, header=True)
                _, ref_median, _ = sigma_clipped_stats(ref_data, sigma=3.0, maxiters=5)
                ref_bg = ref_data - ref_median
                positions = find_sources(
                    ref_data,
                    fwhm=cfg.fwhm,
                    threshold=cfg.threshold_source_detection,
                    edge_cutoff=cfg.edge_cutoff,
                )
                make_star_list(
                    positions,
                    ref_data,
                    cfg.aperture_rad,
                    ctx.layout.reference,
                    os.path.basename(ctx.reference_fits),
                )

            residuals: list[str] = []
            for i, path in enumerate(ctx.preprocessed_files, 1):
                img, head = fits.getdata(path, header=True)
                sci, median = background_subtract(img)
                sx, sy, n_used = select_kernel_stars(
                    ctx.layout.reference,
                    sci,
                    median,
                    cfg.nr_stars,
                    cfg.aperture_rad,
                    random_seed=cfg.random_seed,
                )
                if n_used == 0:
                    raise RuntimeError(f"no kernel stars selected for {path}")
                if use_c:
                    diff = run_c_subtraction(
                        ref_bg,
                        sci,
                        sx,
                        sy,
                        stamp=cfg.stamp,
                        kernel=cfg.kernel,
                        order=cfg.order,
                        code_dir=code_dir,
                    )
                else:
                    diff = optimal_subtract(
                        ref_bg,
                        sci,
                        sx,
                        sy,
                        stamp=cfg.stamp,
                        kernel=cfg.kernel,
                        order=cfg.order,
                    )
                out_name = f"{SUBTRACTED_PREFIX}{Path(path).name}"
                out_path = os.path.join(ctx.layout.residuals, out_name)
                save_fits(diff.astype(np.float32), head, out_path)
                residuals.append(out_path)
                item(
                    i,
                    n_frames,
                    f"{Path(path).name}  kernel stars={n_used}",
                    prefix=ctx.prefix,
                )

            ctx.residual_files = residuals

            if iteration < cfg.num_iterations - 1:
                subtract_background(ctx.layout.residuals, ctx.layout.preprocessed)
                for fp in glob(os.path.join(ctx.layout.residuals, "*.fits")):
                    os.remove(fp)
                ctx.residual_files = []

        return ctx


class DetectAndCrossMatch(Stage):
    name = "detect_and_crossmatch"
    requires = ("optimal_subtract",)

    def apply(self, ctx):
        cfg = ctx.cfg
        step(4, 5, "Detecting and cross-matching sources", prefix=ctx.prefix)
        n_res = len(ctx.residual_files)
        sources_per_image = []
        for i, path in enumerate(ctx.residual_files, 1):
            img, _ = fits.getdata(path, header=True)
            found = find_sources(
                img,
                inverse=True,
                threshold=cfg.threshold_source_detection,
                fwhm=cfg.fwhm,
                edge_cutoff=cfg.edge_cutoff,
            )
            sources_per_image.append(found)
            item(
                i,
                n_res,
                f"{Path(path).name}  {len(found)} detections",
                prefix=ctx.prefix,
            )
        sources_per_image = filter_source_list(
            sources_per_image, cfg.source_filter_threshold
        )
        if not sources_per_image:
            info("No sources remained after filtering", prefix=ctx.prefix)
            ctx.source_list = []
            ctx.sources_csv = None
            return ctx

        ref_starlist = [[xy[0], xy[1], 0] for xy in sources_per_image[0]]
        for elt in sources_per_image[1:]:
            ref_starlist = cross_match(ref_starlist, np.asarray(elt), cfg.match_radius)

        csv_path = os.path.join(ctx.layout.sources, "found_sources.csv")
        ref_head = fits.getheader(ctx.reference_fits)
        with open(csv_path, "w+", newline="", encoding="utf-8") as fp:
            writer = csv.writer(fp)
            if _has_wcs(ref_head):
                sky_coords = pixel_to_sky(ref_starlist, WCS(ref_head))
                writer.writerow(["index", "ra", "dec"])
                for i, sc in enumerate(sky_coords):
                    writer.writerow([i, sc.ra.deg, sc.dec.deg])
            else:
                # Cleaned / WCS-stripped frames: keep pixel positions.
                writer.writerow(["index", "x", "y"])
                for i, xy in enumerate(ref_starlist):
                    writer.writerow([i, xy[0], xy[1]])

        ctx.source_list = ref_starlist
        ctx.sources_csv = csv_path
        info(
            f"Found {len(ref_starlist)} sources after cross-matching",
            prefix=ctx.prefix,
        )
        return ctx



class ExtractLightCurves(Stage):
    name = "extract_lightcurves"
    requires = ("detect_and_crossmatch",)

    def apply(self, ctx):
        cfg = ctx.cfg
        step(5, 5, "Extracting light curves", prefix=ctx.prefix)
        if not ctx.source_list or not ctx.residual_files:
            info("No sources to extract", prefix=ctx.prefix)
            ctx.lightcurve_files = []
            return ctx

        propagate_wcs(ctx.layout.preprocessed, ctx.layout.residuals)
        residual_paths = sorted(ctx.residual_files)
        sources_xy = [[item[0], item[1]] for item in ctx.source_list]
        apertures = CircularAperture(sources_xy, r=cfg.aperture_rad)
        flux, flux_err, time_stamps = measure_flux_timestamps(
            apertures, cfg.aperture_rad, residual_paths
        )
        _, ref_head = fits.getdata(ctx.reference_fits, header=True)
        ctx.lightcurve_files = write_lightcurves(
            flux,
            flux_err,
            time_stamps,
            sources_xy,
            ref_head,
            ctx.layout.lightcurves,
        )
        return ctx


def build_chain():
    return (
        PreprocessFrames()
        >> BuildReference()
        >> OptimalSubtract()
        >> DetectAndCrossMatch()
        >> ExtractLightCurves()
    )
