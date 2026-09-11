"""Photometry / light-curve output tests."""

import numpy as np
import pytest
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from photutils.aperture import CircularAperture, aperture_photometry

from paloma.image_subtraction.core.photometry import (
    measure_flux_timestamps,
    propagate_wcs,
    tstart_to_jd,
    write_lightcurves,
)
from paloma.image_subtraction.io.layout import SUBTRACTED_PREFIX


def _wcs_header() -> fits.Header:
    header = fits.Header()
    header["CTYPE1"] = "RA---TAN"
    header["CTYPE2"] = "DEC--TAN"
    header["CRVAL1"] = 63.5
    header["CRVAL2"] = -60.25
    header["CRPIX1"] = 5.0
    header["CRPIX2"] = 5.0
    header["CD1_1"] = -0.0059
    header["CD1_2"] = 0.0
    header["CD2_1"] = 0.0
    header["CD2_2"] = 0.0059
    return header


def _write_pair(tmp_path, name="frame.fits"):
    """Write a preprocessed frame with a WCS and its prefixed residual."""
    src_dir = tmp_path / "01_preprocessed"
    res_dir = tmp_path / "04_residual_img"
    src_dir.mkdir()
    res_dir.mkdir()

    data = np.zeros((10, 10), dtype=np.float32)
    fits.PrimaryHDU(data, header=_wcs_header()).writeto(src_dir / name)

    # Residuals carry the science header, which has the timestamp but may have
    # lost its WCS.
    res_header = fits.Header()
    res_header["TSTART"] = 1406.65
    fits.PrimaryHDU(data, header=res_header).writeto(
        res_dir / f"{SUBTRACTED_PREFIX}{name}"
    )
    return src_dir, res_dir, res_dir / f"{SUBTRACTED_PREFIX}{name}"


def test_propagate_wcs_matches_across_the_subtracted_prefix(tmp_path):
    """Residuals are named ``subtracted__<frame>``, so the prefix is stripped."""
    src_dir, res_dir, residual = _write_pair(tmp_path)

    propagate_wcs(str(src_dir), str(res_dir))

    header = fits.getheader(residual)
    assert "CTYPE1" in header, "WCS was not propagated onto the residual"
    assert header["CRVAL1"] == 63.5


def test_propagate_wcs_preserves_the_timestamp(tmp_path):
    """A bare ``WCS.to_header()`` has no TSTART, so it must be merged, not swapped."""
    src_dir, res_dir, residual = _write_pair(tmp_path)

    propagate_wcs(str(src_dir), str(res_dir))

    header = fits.getheader(residual)
    assert "TSTART" in header
    assert tstart_to_jd(header) == 2457000.0 + 1406.65


def test_propagate_wcs_does_not_mix_cd_and_pc_conventions(tmp_path):
    """Leaving both matrices in one header makes the WCS ambiguous."""
    src_dir, res_dir, residual = _write_pair(tmp_path)

    propagate_wcs(str(src_dir), str(res_dir))

    header = fits.getheader(residual)
    cd_keys = [k for k in header if k.startswith("CD1_") or k.startswith("CD2_")]
    pc_keys = [k for k in header if k.startswith("PC1_") or k.startswith("PC2_")]
    assert not (cd_keys and pc_keys), f"CD {cd_keys} and PC {pc_keys} both present"


def test_propagate_wcs_skips_unmatched_and_wcs_less_frames(tmp_path):
    """Frames without a counterpart, or without a WCS, are left alone."""
    src_dir = tmp_path / "01_preprocessed"
    res_dir = tmp_path / "04_residual_img"
    src_dir.mkdir()
    res_dir.mkdir()
    data = np.zeros((4, 4), dtype=np.float32)

    # A source frame with no WCS, plus a residual with no source frame at all.
    plain = fits.Header()
    plain["TSTART"] = 5.0
    fits.PrimaryHDU(data, header=plain).writeto(src_dir / "a.fits")
    fits.PrimaryHDU(data, header=plain).writeto(
        res_dir / f"{SUBTRACTED_PREFIX}a.fits"
    )
    fits.PrimaryHDU(data, header=plain).writeto(
        res_dir / f"{SUBTRACTED_PREFIX}orphan.fits"
    )

    propagate_wcs(str(src_dir), str(res_dir))

    for name in (f"{SUBTRACTED_PREFIX}a.fits", f"{SUBTRACTED_PREFIX}orphan.fits"):
        header = fits.getheader(res_dir / name)
        assert "CTYPE1" not in header
        assert header["TSTART"] == 5.0


def test_tstart_to_jd_uses_tess_bjd_offset():
    header = fits.Header()
    header["TSTART"] = 1406.65003008
    assert tstart_to_jd(header) == 2457000.0 + 1406.65003008


def test_tstart_to_jd_uses_header_bjdref():
    header = fits.Header()
    header["TSTART"] = 10.5
    header["BJDREFI"] = 2457000
    header["BJDREFF"] = 0.25
    assert tstart_to_jd(header) == 2457010.75


def test_measure_flux_subtracts_the_mean_background(tmp_path):
    """The aperture background uses the sigma-clipped mean (original algorithm)."""
    rng = np.random.default_rng(0)
    # Right-skewed, so the clipped mean and median are measurably different.
    img = rng.gamma(shape=2.0, scale=5.0, size=(64, 64)).astype(np.float32)
    header = fits.Header()
    header["TSTART"] = 1000.0
    path = tmp_path / f"{SUBTRACTED_PREFIX}frame.fits"
    fits.PrimaryHDU(img, header=header).writeto(path)

    aperture_rad = 3
    apertures = CircularAperture([(32.0, 32.0)], r=aperture_rad)
    flux, _, times = measure_flux_timestamps(apertures, aperture_rad, [str(path)])

    mean, median, _ = sigma_clipped_stats(img, sigma=3.0, maxiters=5)
    raw = float(aperture_photometry(img, apertures)["aperture_sum"][0])
    area = np.pi * aperture_rad**2
    assert mean != pytest.approx(median), "test image is not skewed enough to discriminate"
    assert float(flux[0][0]) == pytest.approx(raw - mean * area, rel=1e-6)
    assert times == [2457000.0 + 1000.0]


def test_write_lightcurves_sets_mission_and_telescop(tmp_path, capsys):
    header = fits.Header()
    header["CAMERA"] = 2
    header["CCD"] = 1
    flux = [[1.0, 2.0], [1.1, 2.1]]
    flux_err = [[0.1, 0.2], [0.11, 0.21]]
    times = [2458000.0, 2458000.5]
    sources = [(10.2, 20.4), (30.7, 40.1)]

    paths = write_lightcurves(flux, flux_err, times, sources, header, str(tmp_path))
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "Value for MISSION is None" not in combined
    assert "Value for TELESCOP is None" not in combined
    assert len(paths) == 2

    hdu = fits.open(paths[0])
    try:
        assert hdu[0].header["TELESCOP"] == "TESS"
        assert hdu[0].header["MISSION"] == "TESS"
        assert hdu[0].header["CAMERA"] == 2
        assert hdu[0].header["CCD"] == 1
        assert hdu[1].data["FLUX"].shape == (2,)
    finally:
        hdu.close()
