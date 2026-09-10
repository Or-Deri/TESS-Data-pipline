"""The dehazer cleaner — scattered-light removal via ``dehaze()``.

Registered under the name ``"dehazer"``. Cleans TESS FFI image cubes
(directory in / directory out).
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any, Dict, Optional

from ..core.cleaner import BaseCleaner, register_cleaner
from ..core.types import CleaningRequest, CleaningResult


@register_cleaner
class DehazerCleaner(BaseCleaner):
    """Remove scattered light from a directory of TESS FFI frames.

    ``strategy`` is kept for metadata / config compatibility (only ``"default"``
    exists). ``params`` are ``DehazeConfig`` overrides; a request may add or
    override values via :attr:`CleaningRequest.params`.
    """

    name = "dehazer"

    def __init__(self, strategy: str = "default", **params: Any) -> None:
        self.strategy = strategy
        self.params: Dict[str, Any] = params

    def clean(self, request: CleaningRequest) -> Optional[CleaningResult]:
        from .dehazer.config import DehazeConfig
        from .dehazer.runner import dehaze

        merged = {**self.params, **request.params}
        merged.pop("strategy", None)
        cfg = self._build_config(DehazeConfig, merged)
        result = dehaze(request.input_dir, request.output_dir, cfg)

        if result.num_outputs == 0:
            return None

        return CleaningResult(
            input_dir=result.input_dir,
            output_dir=result.output_dir,
            outputs=list(result.outputs),
            metadata={
                "cleaner": self.name,
                "strategy": self.strategy,
                **request.metadata,
            },
        )

    @staticmethod
    def _build_config(config_cls, params):
        valid = {f.name for f in fields(config_cls)}
        unknown = set(params) - valid
        if unknown:
            raise ValueError(
                f"Unknown DehazeConfig parameter(s): {sorted(unknown)}. "
                f"Valid parameters: {sorted(valid)}"
            )
        return config_cls(**params)
