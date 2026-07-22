"""Cleaning stage — delegates to a configurable :class:`Cleaner`.

The stage itself contains no algorithm. It holds a
:class:`~paloma.core.cleaner.Cleaner` (chosen by :class:`~paloma.config.CleaningConfig`)
and delegates to it. Swap the algorithm by naming a different registered cleaner
in configuration.
"""

from __future__ import annotations

from typing import Optional, Union

from ..core.cleaner import Cleaner, create_cleaner
from ..core.stage import PipelineStage
from ..core.types import CleaningRequest, CleaningResult


class CleaningStage(PipelineStage[CleaningRequest, CleaningResult]):
    """Run the configured cleaning algorithm over a batch of frames.

    Construct with a registered cleaner name (resolved via the registry) or an
    already-built :class:`Cleaner` instance::

        CleaningStage("dehazer", num_frames=5)      # by name + constructor kwargs
        CleaningStage(DehazerCleaner())             # by instance
        CleaningStage.from_config(CleaningConfig()) # from CleaningConfig
    """

    name = "cleaning"

    def __init__(self, cleaner: Union[str, Cleaner] = "dehazer", **cleaner_kwargs) -> None:
        if isinstance(cleaner, str):
            cleaner = create_cleaner(cleaner, **cleaner_kwargs)
        elif cleaner_kwargs:
            raise TypeError(
                "cleaner_kwargs are only accepted when 'cleaner' is a name (str)"
            )
        self.cleaner: Cleaner = cleaner

    @classmethod
    def from_config(cls, config) -> "CleaningStage":
        """Build the stage from a :class:`~paloma.config.CleaningConfig`."""
        return cls(config.cleaner, **config.params)

    def run(self, data: CleaningRequest) -> Optional[CleaningResult]:
        return self.cleaner.clean(data)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<CleaningStage cleaner={getattr(self.cleaner, 'name', self.cleaner)!r}>"
