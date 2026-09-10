"""Photometry / light-curve output tests."""

from astropy.io import fits

from paloma.image_subtraction.core.photometry import tstart_to_jd, write_lightcurves


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
