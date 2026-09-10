"""Cleaner registry / DehazerCleaner smoke tests."""

from paloma import DehazerCleaner, available_cleaners, create_cleaner
from paloma.cleaning.dehazer import DehazeResult, dehaze


def test_dehazer_registered():
    assert "dehazer" in available_cleaners()
    cleaner = create_cleaner("dehazer", strategy="default", num_frames=2)
    assert isinstance(cleaner, DehazerCleaner)
    assert cleaner.strategy == "default"
    assert cleaner.params["num_frames"] == 2


def test_dehaze_result_collect(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "dehazed__a.fits").write_bytes(b"")
    (out / "other.fits").write_bytes(b"")
    result = DehazeResult.collect("default", str(tmp_path / "in"), str(out))
    assert result.num_outputs == 1
    assert result.outputs[0].endswith("dehazed__a.fits")


def test_dehaze_is_callable():
    assert callable(dehaze)
