"""Image-subtraction stage — runs after cleaning, delegates to a :class:`Subtractor`."""

from __future__ import annotations

from typing import Optional, Union

from ..config import ImageSubtractionConfig
from ..core.stage import PipelineStage
from ..core.subtractor import Subtractor, create_subtractor
from ..core.types import CleaningResult, SubtractionRequest, SubtractionResult


class ImageSubtractionStage(PipelineStage[SubtractionRequest, SubtractionResult]):
    """Run optimal image subtraction on cleaned (or raw) FFI frames.

    This stage sits **after** :class:`~paloma.stages.cleaning.CleaningStage` in
    the pipeline. It is not a cleaner.

        ImageSubtractionStage.from_config(ImageSubtractionConfig())
        stage.run(SubtractionRequest.from_cleaning(cleaning_result, "out/subtracted"))
    """

    name = "image_subtraction"

    def __init__(
        self,
        subtractor: Union[str, Subtractor] = "default",
        **subtractor_kwargs,
    ) -> None:
        if isinstance(subtractor, str):
            subtractor = create_subtractor(subtractor, **subtractor_kwargs)
        elif subtractor_kwargs:
            raise TypeError(
                "subtractor_kwargs are only accepted when 'subtractor' is a name (str)"
            )
        self.subtractor: Subtractor = subtractor

    @classmethod
    def from_config(cls, config: ImageSubtractionConfig) -> "ImageSubtractionStage":
        return cls(config.subtractor, **config.params)

    def run(self, data: SubtractionRequest) -> Optional[SubtractionResult]:
        return self.subtractor.subtract(data)

    def run_after_cleaning(
        self,
        cleaning: CleaningResult,
        output_dir: str,
        **params,
    ) -> Optional[SubtractionResult]:
        """Convenience: chain directly from a :class:`CleaningResult`."""
        return self.run(
            SubtractionRequest.from_cleaning(cleaning, output_dir, **params)
        )

    def __repr__(self) -> str:
        return f"<ImageSubtractionStage subtractor={getattr(self.subtractor, 'name', self.subtractor)!r}>"
