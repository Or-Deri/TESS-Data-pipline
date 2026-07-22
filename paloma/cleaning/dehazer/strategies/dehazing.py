"""The default (spatio-temporal) dehazing strategy."""

from ..config import DehazeConfig
from ..pipeline import dehaze
from .base import BaseDehazer
from .registry import register_strategy


@register_strategy
class DehazingStrategy(BaseDehazer):
    """The default dehazer: spatio-temporal (3-D) blind dehazing.

    Global normalization across the batch plus Gaussian temporal smoothing of
    both airlight and transmission, for time-ordered sector sequences where
    temporal consistency and noise reduction matter most.
    """

    label = "default"

    def _run(self, input_dir: str, output_dir: str, cfg: DehazeConfig) -> None:
        dehaze(input_dir, output_dir, cfg)
