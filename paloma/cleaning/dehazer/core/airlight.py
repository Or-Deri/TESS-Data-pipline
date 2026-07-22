"""Airlight estimation (Step 1 back-end).

Closed-form pairwise airlight plus the iteratively-reweighted global estimate.
See ``docs/workflow/03-estimate-airlight.md``.
"""

import numpy as np


def estimate_pairwise_airlight(p1, p2):
    """Closed-form pairwise airlight from a higher-contrast-first pair.

    Solves the least-squares ratio ``<diff, cross> / <diff, diff>`` (thesis
    Eq. 3.7). Returns ``None`` if the denominator is below ``1e-6``.
    """
    p1 = np.asarray(p1, dtype=np.float64)
    p2 = np.asarray(p2, dtype=np.float64)

    t1 = p1 - p1.mean()
    t2 = p2 - p2.mean()

    diff = (t2 - t1).ravel()
    cross = (p1 * t2 - p2 * t1).ravel()

    denom = float(np.dot(diff, diff))
    if denom < 1e-6:
        return None
    return float(np.dot(diff, cross) / denom)


def _t_lower_bound(patch, a):
    """Per-patch transmission lower bound ``max_x(1 - patch/max(a, 1e-6))``."""
    a_safe = max(float(a), 1e-6)
    return float(np.max(1.0 - np.asarray(patch, dtype=np.float64) / a_safe))


def estimate_airlight(pairs, num_iterations=10):
    """Iteratively re-weighted global airlight estimate for one frame.

    Weights up-weight pairs with a large transmission contrast between the two
    patches. Falls back to ``0.5`` when no valid pairwise estimates exist.

    Re-weighting indexes the original ``pairs`` list with
    ``i < len(pairwise_as)`` (same as the reference implementation) — not a
    filtered parallel list of only-valid pairs.
    """
    if not pairs:
        print("    No pairs available, defaulting A=0.5")
        return 0.5

    pairwise_as = [
        a
        for a in (estimate_pairwise_airlight(p1, p2) for p1, p2 in pairs)
        if a is not None and 0.0 <= a <= 1.0
    ]

    if not pairwise_as:
        print("    No valid pairwise estimates, defaulting A=0.5")
        return 0.5

    global_a = float(np.mean(pairwise_as))
    print(
        f"    Pairwise estimates: {len(pairwise_as)} valid out of "
        f"{len(pairs)} pairs, initial A={global_a:.4f}"
    )

    for iteration in range(num_iterations):
        weights = []
        valid_indices = []
        for i, (p1, p2) in enumerate(pairs):
            if i >= len(pairwise_as):
                continue
            t_lb1 = _t_lower_bound(p1, global_a)
            t_lb2 = _t_lower_bound(p2, global_a)
            if t_lb2 < 1e-6:
                continue
            w = ((t_lb1 - t_lb2) * (t_lb1 / t_lb2 - 1.0)) ** 2
            weights.append(w)
            valid_indices.append(i)

        if np.sum(weights) > 1e-6:
            valid_as = [pairwise_as[i] for i in valid_indices]
            global_a = float(np.average(valid_as, weights=weights))
        else:
            global_a = float(np.mean(pairwise_as))

        if (iteration + 1) % 5 == 0 or iteration == 0:
            print(
                f"    Iteration {iteration + 1}/{num_iterations}: "
                f"A={global_a:.6f}, {len(valid_indices)} weighted pairs"
            )

    final_a = float(np.clip(global_a, 0.0, 1.0))
    print(f"    Final airlight: A={final_a:.6f}")
    return final_a
