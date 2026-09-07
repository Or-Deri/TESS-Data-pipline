"""Output directory layout for a subtraction run."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class RunLayout:
    root: str
    preprocessed: str
    masters: str
    reference: str
    residuals: str
    sources: str
    lightcurves: str

    @classmethod
    def create(cls, output_dir: str) -> "RunLayout":
        root = os.path.abspath(output_dir)
        paths = {
            "preprocessed": "01_preprocessed",
            "masters": "02_masters_frames",
            "reference": "03_ref_data",
            "residuals": "04_residual_img",
            "sources": "05_sources",
            "lightcurves": "06_lightcurves",
        }
        layout = cls(
            root=root,
            preprocessed=os.path.join(root, paths["preprocessed"]),
            masters=os.path.join(root, paths["masters"]),
            reference=os.path.join(root, paths["reference"]),
            residuals=os.path.join(root, paths["residuals"]),
            sources=os.path.join(root, paths["sources"]),
            lightcurves=os.path.join(root, paths["lightcurves"]),
        )
        for path in (
            layout.preprocessed,
            layout.masters,
            layout.reference,
            layout.residuals,
            layout.sources,
            layout.lightcurves,
        ):
            os.makedirs(path, exist_ok=True)
        return layout
