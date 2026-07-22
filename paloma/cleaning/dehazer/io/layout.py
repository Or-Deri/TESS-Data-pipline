"""Structured (notebook-style) output path construction.

See ``docs/workflow/06-recover-save.md`` and ``02-load-normalize.md``.
"""

import os
import re


def infer_sector_label(input_dir, files=None):
    """Infer a TESS sector label like ``s0003-1-1`` from dir name or filenames."""
    base = os.path.basename(os.path.normpath(input_dir))
    if re.match(r"^s\d+-\d+-\d+$", base):
        return base

    if files:
        m = re.search(r"-s(\d+-\d+-\d+)-", os.path.basename(files[0]))
        if m:
            return "s" + m.group(1)

    sanitized = re.sub(r"[^\w.\-]+", "_", base)
    return sanitized or "unknown_sector"


def _format_vt(vt):
    if vt == 0:
        return "0"
    if abs(vt) >= 1e-2:
        return f"{vt:g}"
    if abs(vt) >= 1e-12:
        return f"{vt:.12f}".rstrip("0").rstrip(".")
    return f"{vt:.6g}"


def _format_nnd(nnd):
    if float(nnd).is_integer():
        return str(int(nnd))
    return f"{nnd:g}"


def params_folder_name(cfg):
    """Slug encoding the key params, e.g. ``ps9_vt0.00005_nnd0.3``."""
    return (
        f"ps{cfg.patch_size}"
        f"_vt{_format_vt(cfg.variance_threshold)}"
        f"_nnd{_format_nnd(cfg.nn_dist_threshold)}"
    )


def structured_dehaze_output_dir(output_base, cfg, input_dir, files=None):
    """Build ``{base}/output_{sector}_GlobalNorm_Subfolders/{slug}/``."""
    sector = infer_sector_label(input_dir, files)
    slug = params_folder_name(cfg)
    return os.path.join(
        output_base, f"output_{sector}_GlobalNorm_Subfolders", slug
    )
