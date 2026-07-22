"""Patch extraction and co-occurrence pairing (Step 1 front-end).

See ``docs/workflow/03-estimate-airlight.md``.
"""

import numpy as np

from .backend import (
    find_nearest_neighbors,
    get_array_module,
    sliding_window_view,
    to_cpu,
)


def extract_patches(image, patch_size=9, variance_threshold=5e-5, max_patches=None):
    """Extract high-variance patches and their unit L2 descriptors.

    Returns ``(original_patches, normalized_flat)`` where ``original_patches``
    are the raw ``p x p`` kept patches and ``normalized_flat`` are the
    mean-subtracted, L2-normalized descriptor vectors of shape ``(K, p*p)``.
    Empty arrays are returned when nothing qualifies.
    """
    xp = get_array_module(image)
    p = patch_size

    windows = sliding_window_view(image, p)
    hh, ww = windows.shape[:2]
    patches = windows.reshape(hh * ww, p, p)
    total_patches = patches.shape[0]

    variances = xp.var(patches, axis=(1, 2))
    keep = xp.where(variances > variance_threshold)[0]
    num_high_var = int(keep.shape[0])

    if max_patches is not None and keep.shape[0] > int(max_patches):
        # NOTE: unseeded on purpose to match the reference (default None avoids it).
        sel = np.random.choice(int(keep.shape[0]), int(max_patches), replace=False)
        sel = xp.asarray(sel) if xp is not np else sel
        keep = keep[sel]
        print(
            f"    Patches: {total_patches} total, {num_high_var} high-variance, "
            f"subsampled to {int(keep.shape[0])}"
        )
    else:
        print(
            f"    Patches: {total_patches} total, {num_high_var} above "
            f"variance threshold ({variance_threshold})"
        )

    if keep.shape[0] == 0:
        print("    WARNING: No high-variance patches found")
        empty_p = xp.empty((0, p, p), dtype=image.dtype)
        empty_d = xp.empty((0, p * p), dtype=image.dtype)
        return empty_p, empty_d

    original = patches[keep]
    means = original.mean(axis=(1, 2), keepdims=True)
    centered = original - means
    flat = centered.reshape(original.shape[0], -1)
    norms = xp.linalg.norm(flat, axis=1)

    valid = norms > 1e-6
    if not bool(xp.any(valid)):
        print("    WARNING: All patches have near-zero norm after centering")
        empty_p = xp.empty((0, p, p), dtype=image.dtype)
        empty_d = xp.empty((0, p * p), dtype=image.dtype)
        return empty_p, empty_d

    original = original[valid]
    flat = flat[valid]
    norms = norms[valid]
    normalized = flat / norms[:, None]
    print(f"    Kept {int(original.shape[0])} patches after L2-normalization")
    return original, normalized


def find_pairs(original_patches, descriptors, nn_dist_threshold=0.3):
    """Form co-occurring patch pairs from nearest-neighbour descriptor matches.

    Each accepted pair (``nn_dist < nn_dist_threshold``, strictly) is ordered so
    the higher-contrast (larger std) patch comes first. Always returns CPU
    NumPy tuples.
    """
    if descriptors.shape[0] < 2:
        print("    Too few patches for pairing (<2)")
        return []

    print(
        f"    Searching {int(original_patches.shape[0])} descriptors "
        f"for nearest neighbors ..."
    )
    nn_idx, nn_dist = find_nearest_neighbors(descriptors)
    nn_idx = to_cpu(nn_idx)
    nn_dist = to_cpu(nn_dist)
    original_cpu = to_cpu(original_patches)

    if nn_dist.shape[0] > 0:
        print(
            f"    NN distances: min={nn_dist.min():.4f}, "
            f"median={np.median(nn_dist):.4f}, "
            f"max={nn_dist.max():.4f}"
        )

    pairs = []
    for i in range(nn_dist.shape[0]):
        if nn_dist[i] < nn_dist_threshold:
            p_i = original_cpu[i]
            p_nn = original_cpu[int(nn_idx[i])]
            if np.std(p_i) >= np.std(p_nn):
                pairs.append((p_i, p_nn))
            else:
                pairs.append((p_nn, p_i))

    print(f"    Found {len(pairs)} co-occurring pairs (threshold={nn_dist_threshold})")
    return pairs
