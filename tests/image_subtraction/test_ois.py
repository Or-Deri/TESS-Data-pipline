"""Unit tests for the pure-Python OIS engine.

These guard the linear solve behind the kernel fit. It previously mis-indexed
its substitution passes and returned an approximate answer, which made the
image-subtraction ground-truth test fail; nothing exercised it directly.
"""

import numpy as np
import pytest
from scipy.ndimage import correlate

from paloma.image_subtraction.core.ois import _lu_solve, optimal_subtract

STAR_X = np.array([16, 32, 48, 20, 44])
STAR_Y = np.array([16, 32, 48, 44, 20])


def _reference_image(seed: int = 1, size: int = 64) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random((size, size)) * 10.0 + 5.0


@pytest.mark.parametrize("q", [3, 5, 25, 75])
def test_lu_solve_matches_numpy(q):
    """The solver must actually solve ``C a = d``, not approximate it."""
    rng = np.random.default_rng(0)
    m = rng.normal(size=(q, q))
    matrix = m @ m.T + q * np.eye(q)  # symmetric positive definite, like the normal equations
    rhs = rng.normal(size=q)

    # ``optimal_subtract`` accumulates element (row, col) at ``row + col * q``.
    solution = _lu_solve(matrix.ravel(order="F").copy(), rhs.copy(), q)

    np.testing.assert_allclose(solution, np.linalg.solve(matrix, rhs), rtol=1e-10, atol=1e-12)
    np.testing.assert_allclose(matrix @ solution, rhs, rtol=1e-10, atol=1e-12)


def test_lu_solve_reads_column_major_layout():
    """A deliberately asymmetric system pins down the expected flat layout."""
    matrix = np.array([[4.0, 1.0, 0.0], [2.0, 5.0, 1.0], [0.0, 1.0, 3.0]])
    rhs = np.array([1.0, 2.0, 3.0])

    solution = _lu_solve(matrix.ravel(order="F").copy(), rhs.copy(), 3)

    np.testing.assert_allclose(solution, np.linalg.solve(matrix, rhs), rtol=1e-12, atol=1e-14)


def test_lu_solve_falls_back_on_singular_system():
    """Under-constrained fits must yield finite coefficients, not raise."""
    q = 6
    matrix = np.zeros((q, q))
    matrix[:3, :3] = np.eye(3)

    solution = _lu_solve(matrix.ravel(order="F"), np.ones(q), q)

    assert solution.shape == (q,)
    assert np.all(np.isfinite(solution))


@pytest.mark.parametrize("scale", [1.0, 2.5, 0.4])
def test_optimal_subtract_recovers_flux_rescale(scale):
    """A pure flux rescale is exactly recoverable, so the residual must vanish.

    The fitted kernel is a centred delta, which needs no padding inside the
    stamps, making this the one case with no stamp-edge bias. The broken solver
    left residuals of order 1e-2 here.
    """
    ref = _reference_image()

    residual = optimal_subtract(
        ref, ref * scale, STAR_X, STAR_Y, stamp=3, kernel=2, order=0
    )

    assert np.abs(residual).max() < 1e-9


def test_optimal_subtract_shrinks_residual_for_a_known_kernel():
    """A smoothing kernel is recovered well enough to suppress the source flux.

    It is not recovered exactly: the normal equations correlate each stamp with
    ``mode="constant"``, so only the inner ``kernel``-trimmed part of every
    stamp is free of zero-padding bias. That is inherited from the reference C
    implementation, so this asserts suppression rather than exactness.
    """
    ref = _reference_image()
    kernel = np.zeros((5, 5))
    kernel[2, 2], kernel[1, 2], kernel[3, 2] = 0.6, 0.15, 0.15
    kernel[2, 1], kernel[2, 3] = 0.05, 0.05
    science = correlate(ref, kernel, mode="constant")

    residual = optimal_subtract(
        ref, science, STAR_X, STAR_Y, stamp=3, kernel=2, order=0
    )

    assert np.abs(residual).max() < 0.2 * np.abs(science).max()


def test_optimal_subtract_returns_science_minus_model():
    """Sign convention: a positive excess in science stays positive."""
    ref = _reference_image()
    science = ref.copy()
    science[30, 30] += 500.0

    residual = optimal_subtract(
        ref, science, STAR_X, STAR_Y, stamp=3, kernel=2, order=0
    )

    assert residual[30, 30] > 100.0
