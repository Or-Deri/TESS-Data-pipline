"""The dehazer cleaner — scattered-light removal via the ``dehazer`` engine.

This is *one* implementation of the pipeline-level
:class:`~paloma.core.cleaner.Cleaner` interface (registered under the name
``"dehazer"``). It adapts the dehazing engine at
:mod:`paloma.cleaning.dehazer` — the merged TESS dehazing project — by
delegating to its public Strategy API (``DehazingContext`` / ``DehazeConfig``),
so the algorithm stays swappable without touching the pipeline.

Scope note: the dehazer cleans TESS FFI *image cubes* (2-D frames over time),
not 1-D light curves, so it runs at the image level (before per-target
light-curve extraction) with a directory-based request/result.

The heavy engine import is deferred to :meth:`clean`, so importing this module
(which is what registers the cleaner) stays cheap and does not require the
scientific dependencies to be installed.
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any, Dict, Optional

from ..core.cleaner import BaseCleaner, register_cleaner
from ..core.types import CleaningRequest, CleaningResult


@register_cleaner
class DehazerCleaner(BaseCleaner):
    """Remove scattered light from a directory of TESS FFI frames.

    ``strategy`` selects one of the engine's *internal* dehazing strategies (its
    own Strategy registry; default ``"default"``). ``params`` are
    configuration-time ``DehazeConfig`` overrides; a request may add or override
    individual values at run time via :attr:`CleaningRequest.params`.
    """

    name = "dehazer"

    def __init__(self, strategy: str = "default", **params: Any) -> None:
        self.strategy = strategy
        self.params: Dict[str, Any] = params

    def clean(self, request: CleaningRequest) -> Optional[CleaningResult]:
        from .dehazer import DehazeConfig, DehazingContext

        merged = {**self.params, **request.params}
        cfg = self._build_config(DehazeConfig, merged)
        context = DehazingContext.from_label(self.strategy)
        result = context.execute(request.input_dir, request.output_dir, cfg)

        # Chain-of-responsibility: no cleaned frames -> stop the pipeline.
        if result.num_outputs == 0:
            return None

        return CleaningResult(
            input_dir=result.input_dir,
            output_dir=result.output_dir,
            outputs=list(result.outputs),
            metadata={"cleaner": self.name, "strategy": result.label, **request.metadata},
        )

    @staticmethod
    def _build_config(config_cls, params):
        """Build a ``DehazeConfig``, applying only recognized overrides."""
        valid = {f.name for f in fields(config_cls)}
        unknown = set(params) - valid
        if unknown:
            raise ValueError(
                f"Unknown DehazeConfig parameter(s): {sorted(unknown)}. "
                f"Valid parameters: {sorted(valid)}"
            )
        return config_cls(**params)
