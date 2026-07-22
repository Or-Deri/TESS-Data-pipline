"""Internal consistency of the dehazing pipeline (no external reference needed).

Two properties that must hold without comparing against any other
implementation: the pipeline is deterministic for a fixed config, and the fluent
``DehazePipeline`` facade produces the same FITS as the ``dehaze()`` entry point.
"""

from conftest import assert_outputs_match


def _run(input_dir, output_dir, cfg_kwargs):
    from paloma.cleaning.dehazer.config import DehazeConfig
    from paloma.cleaning.dehazer.pipeline import dehaze

    dehaze(str(input_dir), str(output_dir), DehazeConfig(**cfg_kwargs))


def test_dehaze_is_deterministic(synthetic_fits, cfg_kwargs, tmp_path):
    """Two runs with the same config produce bit-for-bit identical FITS."""
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"

    _run(synthetic_fits, out_a, cfg_kwargs)
    _run(synthetic_fits, out_b, cfg_kwargs)

    n = assert_outputs_match(out_a, out_b)
    assert n == cfg_kwargs["num_frames"]


def test_fluent_facade_matches_dehaze(synthetic_fits, cfg_kwargs, tmp_path):
    """The DehazePipeline fluent API produces the same FITS as dehaze()."""
    from paloma.cleaning.dehazer.config import DehazeConfig
    from paloma.cleaning.dehazer.io import load_fits_directory
    from paloma.cleaning.dehazer.pipeline import DehazePipeline, dehaze

    out_run = tmp_path / "run"
    out_fluent = tmp_path / "fluent"
    cfg = DehazeConfig(**cfg_kwargs)

    dehaze(str(synthetic_fits), str(out_run), cfg)

    out_fluent.mkdir(parents=True, exist_ok=True)
    cube, metadata = load_fits_directory(str(synthetic_fits), cfg)
    DehazePipeline(cfg).load(cube, metadata).run(str(out_fluent))

    assert_outputs_match(out_run, out_fluent)
