"""Source-detection column-name tests."""

import warnings

import numpy as np
from astropy.table import QTable

from paloma.image_subtraction.core.sources import _centroid_xy, find_sources


def test_centroid_xy_prefers_new_column_names():
    table = QTable({"x_centroid": [1.5], "y_centroid": [2.5]})
    assert _centroid_xy(table) == [(1.5, 2.5)]


def test_centroid_xy_falls_back_to_legacy_names():
    table = QTable({"xcentroid": [3.0], "ycentroid": [4.0]})
    assert _centroid_xy(table) == [(3.0, 4.0)]


def test_find_sources_does_not_use_deprecated_centroid_names():
    yy, xx = np.mgrid[0:64, 0:64]
    img = 50.0 * np.exp(-((xx - 32.0) ** 2 + (yy - 32.0) ** 2) / (2 * 1.5**2))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        positions = find_sources(img, threshold=3.0, fwhm=2.0, edge_cutoff=3)
    messages = " ".join(str(w.message) for w in caught)
    assert "xcentroid" not in messages
    assert "ycentroid" not in messages
    assert positions
    x, y = positions[0]
    assert abs(x - 32) < 2
    assert abs(y - 32) < 2
