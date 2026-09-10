"""End-to-end Cleaning → Image Subtraction pipeline and stage wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from .config import ImageSubtractionConfig, PipelineConfig
from .core.cleaner import Cleaner, create_cleaner
from .core.stage import PipelineStage
from .core.subtractor import Subtractor, create_subtractor
from .core.types import (
    CleaningRequest,
    CleaningResult,
    SubtractionRequest,
    SubtractionResult,
)


class CleaningStage(PipelineStage[CleaningRequest, CleaningResult]):
    """Run the configured cleaning algorithm over a batch of frames."""

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
        return cls(config.cleaner, **config.params)

    def run(self, data: CleaningRequest) -> Optional[CleaningResult]:
        return self.cleaner.clean(data)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<CleaningStage cleaner={getattr(self.cleaner, 'name', self.cleaner)!r}>"


class ImageSubtractionStage(PipelineStage[SubtractionRequest, SubtractionResult]):
    """Run optimal image subtraction on cleaned (or raw) FFI frames."""

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
        return (
            f"<ImageSubtractionStage subtractor="
            f"{getattr(self.subtractor, 'name', self.subtractor)!r}>"
        )


@dataclass
class PipelineResult:
    """Outcome of a full pipeline run."""

    cleaning: Optional[CleaningResult]
    subtraction: Optional[SubtractionResult]

    @property
    def ok(self) -> bool:
        return self.cleaning is not None and self.subtraction is not None


class Pipeline:
    """Run cleaning then image subtraction, chaining via directory contracts."""

    def __init__(
        self,
        cleaning: CleaningStage,
        subtraction: ImageSubtractionStage,
        config: Optional[PipelineConfig] = None,
    ) -> None:
        self.cleaning = cleaning
        self.subtraction = subtraction
        self.config = config or PipelineConfig()

    @classmethod
    def from_config(cls, config: PipelineConfig) -> "Pipeline":
        return cls(
            CleaningStage.from_config(config.cleaning),
            ImageSubtractionStage.from_config(config.subtraction),
            config,
        )

    @classmethod
    def from_env(cls, *, load_dotenv: bool = True) -> "Pipeline":
        return cls.from_config(PipelineConfig.from_env(load_dotenv=load_dotenv))

    def run(
        self,
        input_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        cleaned_dir: Optional[str] = None,
        subtracted_dir: Optional[str] = None,
    ) -> PipelineResult:
        """Execute cleaning then subtraction."""
        cfg = self.config
        in_dir = input_dir or cfg.input_dir
        if not in_dir:
            raise ValueError(
                "input_dir is required (pass it or set PALOMA_INPUT_DIR in .env)"
            )

        out_root = output_dir or cfg.output_dir or "results"
        clean_out = cleaned_dir or cfg.resolve_cleaned_dir(out_root)
        sub_out = subtracted_dir or cfg.resolve_subtracted_dir(out_root)

        cleaned = self.cleaning.run(
            CleaningRequest(input_dir=in_dir, output_dir=clean_out)
        )
        if cleaned is None:
            return PipelineResult(cleaning=None, subtraction=None)

        subtracted = self.subtraction.run_after_cleaning(cleaned, sub_out)
        return PipelineResult(cleaning=cleaned, subtraction=subtracted)
