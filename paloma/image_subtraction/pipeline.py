"""Pipeline orchestration and strategy layer for image subtraction."""

from __future__ import annotations

import glob
import os
import time
from dataclasses import fields

from .config import SubtractionConfig
from ..core.subtractor import BaseSubtractor, register_subtractor
from ..core.types import SubtractionRequest, SubtractionResult
from .io.layout import RunLayout
from .workflow import SubtractionWorkflowContext, build_chain


def subtract(input_dir: str, output_dir: str, cfg: SubtractionConfig) -> SubtractionResult:
    """Run the full OIS pipeline over a directory of FITS frames."""
    os.makedirs(output_dir, exist_ok=True)
    layout = RunLayout.create(output_dir)
    chain = build_chain()
    ctx = SubtractionWorkflowContext(
        cfg=cfg,
        input_dir=os.path.abspath(input_dir),
        output_dir=os.path.abspath(output_dir),
        layout=layout,
    )
    start = time.time()
    print(f"\n{'=' * 60}")
    print("  Optimal Image Subtraction Pipeline")
    print(f"  Input:  {ctx.input_dir}")
    print(f"  Output: {ctx.output_dir}")
    print(f"{'=' * 60}")
    chain.run(ctx)
    print(f"\nPipeline complete in {time.time() - start:.1f}s.")
    return SubtractionResult(
        input_dir=ctx.input_dir,
        output_dir=ctx.output_dir,
        outputs=sorted(ctx.residual_files),
        sources_csv=ctx.sources_csv,
        lightcurve_dir=ctx.layout.lightcurves if ctx.lightcurve_files else None,
        reference_fits=ctx.reference_fits,
        metadata={"residual_count": len(ctx.residual_files)},
    )


@register_subtractor
class DefaultSubtractor(BaseSubtractor):
    """Default OIS subtractor backed by :mod:`paloma.image_subtraction`."""

    name = "default"

    def __init__(self, strategy: str = "default", **params):
        self.strategy = strategy
        self.params = params

    def subtract(self, request: SubtractionRequest) -> SubtractionResult | None:
        merged = {**self.params, **request.params}
        cfg = self._build_config(SubtractionConfig, merged)
        result = subtract(request.input_dir, request.output_dir, cfg)
        if result.num_outputs == 0:
            return None
        result.metadata = {
            "subtractor": self.name,
            "strategy": self.strategy,
            **request.metadata,
            **result.metadata,
        }
        return result

    @staticmethod
    def _build_config(config_cls, params):
        valid = {f.name for f in fields(config_cls)}
        unknown = set(params) - valid
        if unknown:
            raise ValueError(
                f"Unknown SubtractionConfig parameter(s): {sorted(unknown)}. "
                f"Valid parameters: {sorted(valid)}"
            )
        return config_cls(**params)
