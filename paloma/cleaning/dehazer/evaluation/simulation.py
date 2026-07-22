"""Synthetic data generation and quantitative validation harness.

See ``docs/workflow/08-verification.md``. This is a validation *convenience*
path: sim files are read from HDU 0 and the transmission clamp is
``[t_min_clip, 1.0]`` (simpler than the production ``[0.01, 0.9]``).
"""

import os

import numpy as np
from astropy.io import fits
from scipy.ndimage import gaussian_filter, gaussian_filter1d
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

from ..config import DehazeConfig
from ..core import (
    estimate_airlight,
    extract_patches,
    find_pairs,
    guided_filter,
    recover_image,
)
from ..io import normalize

_GROUND_TRUTH_NAME = "ground_truth.fits"
_CLOUD_SEED = 999


def generate_amorphous_cloud(clean, num_frames=10):
    """Build a stray-light cube ``I_clean + S(x, tau) + eta`` (thesis Sec. 4.1.1).

    A coherent-noise texture (``gaussian_filter``, sigma=30) modulated by a
    moving spatial envelope with peak intensity ~20x the median background,
    plus small Gaussian read noise. Deterministic given ``np.random.seed(999)``.
    """
    np.random.seed(_CLOUD_SEED)
    clean = np.asarray(clean, dtype=np.float64)
    h, w = clean.shape

    median_bg = float(np.median(clean))
    scale = median_bg if median_bg > 0 else float(np.mean(clean)) or 1.0
    peak = 20.0 * scale

    texture = gaussian_filter(np.random.rand(h, w), sigma=30)
    tmax = float(texture.max())
    if tmax > 0:
        texture = texture / tmax

    yy, xx = np.mgrid[0:h, 0:w]
    sigma_env = w / 3.0
    frames = []
    for tau in range(num_frames):
        cx = w * (tau + 1) / (num_frames + 1)
        envelope = np.exp(-((xx - cx) ** 2) / (2.0 * sigma_env ** 2))
        stray = peak * texture * envelope
        eta = np.random.normal(0.0, 1e-3 * peak, size=(h, w))
        frames.append(clean + stray + eta)
    return np.stack(frames, axis=0)


def generate_null_test(clean, num_frames=10):
    """A control cube with no stray light (each frame == clean)."""
    clean = np.asarray(clean, dtype=np.float64)
    return np.stack([clean.copy() for _ in range(num_frames)], axis=0)


def run_simulation(output_dir, clean_fits, sim_type="cloud", num_frames=10):
    """Generate a synthetic sequence and write it (plus ground truth) to disk."""
    os.makedirs(output_dir, exist_ok=True)
    with fits.open(clean_fits) as hdul:
        clean = np.asarray(hdul[0].data, dtype=np.float64)
    clean = np.nan_to_num(clean)

    if sim_type == "cloud":
        cube = generate_amorphous_cloud(clean, num_frames)
    elif sim_type == "null":
        cube = generate_null_test(clean, num_frames)
    else:
        raise ValueError(f"Unknown simulation type {sim_type!r}")

    fits.PrimaryHDU(clean).writeto(
        os.path.join(output_dir, _GROUND_TRUTH_NAME), overwrite=True
    )
    for i in range(cube.shape[0]):
        fits.PrimaryHDU(cube[i]).writeto(
            os.path.join(output_dir, f"sim_{i:03d}.fits"), overwrite=True
        )
    return output_dir


def evaluate_metrics(recovered, gt):
    """Return MSE / PSNR / SSIM with ``data_range = gt.max() - gt.min()``."""
    recovered = np.asarray(recovered, dtype=np.float64)
    gt = np.asarray(gt, dtype=np.float64)
    data_range = float(gt.max() - gt.min())
    mse = float(np.mean((recovered - gt) ** 2))
    psnr = float(peak_signal_noise_ratio(gt, recovered, data_range=data_range))
    ssim = float(structural_similarity(gt, recovered, data_range=data_range))
    return {"mse": mse, "psnr": psnr, "ssim": ssim}


def run_validation(sim_dir, output_dir, cfg=None):
    """Dehaze a synthetic sequence and score the middle recovered frame.

    Uses the simplified validation transmission clamp ``[t_min_clip, 1.0]``.
    """
    if cfg is None:
        cfg = DehazeConfig()
    os.makedirs(output_dir, exist_ok=True)

    sim_files = sorted(
        f
        for f in os.listdir(sim_dir)
        if f.startswith("sim_") and f.endswith(".fits")
    )
    if not sim_files:
        raise FileNotFoundError(f"No sim_*.fits found in {sim_dir!r}")

    frames = []
    for name in sim_files:
        with fits.open(os.path.join(sim_dir, name)) as hdul:
            frames.append(np.nan_to_num(np.asarray(hdul[0].data, dtype=np.float64)))

    with fits.open(os.path.join(sim_dir, _GROUND_TRUTH_NAME)) as hdul:
        gt = np.nan_to_num(np.asarray(hdul[0].data, dtype=np.float64))

    global_min = min(float(np.min(fr)) for fr in frames)
    global_max = max(float(np.max(fr)) for fr in frames)
    cube = np.stack([normalize(fr, global_min, global_max) for fr in frames], axis=0)
    n = cube.shape[0]

    raw_airlights = []
    for i in range(n):
        original, descriptors = extract_patches(
            cube[i], cfg.patch_size, cfg.variance_threshold, cfg.max_patches
        )
        pairs = find_pairs(original, descriptors, cfg.nn_dist_threshold)
        raw_airlights.append(estimate_airlight(pairs, cfg.num_iterations))

    a = gaussian_filter1d(np.array(raw_airlights), sigma=cfg.sigma_temporal, axis=0)

    t_cube = np.zeros_like(cube)
    for i in range(n):
        a_safe = max(float(a[i]), 1e-6)
        t_initial = np.clip(1.0 - cube[i] / a_safe, cfg.t_min_clip, 1.0)
        t_cube[i] = guided_filter(
            cube[i], t_initial, cfg.guided_filter_radius, cfg.guided_filter_eps
        )
    t_cube = gaussian_filter1d(t_cube, sigma=cfg.sigma_temporal, axis=0)

    mid = n // 2
    recovered = recover_image(cube[mid], a[mid], t_cube[mid], cfg.t_min_clip)
    gt_norm = normalize(gt, global_min, global_max)

    metrics = evaluate_metrics(recovered, gt_norm)
    fits.PrimaryHDU(np.asarray(recovered, dtype=np.float64)).writeto(
        os.path.join(output_dir, "recovered_mid.fits"), overwrite=True
    )
    print(
        f"[validate] MSE={metrics['mse']:.6g} "
        f"PSNR={metrics['psnr']:.4f} dB SSIM={metrics['ssim']:.4f}"
    )
    return metrics
