"""Device-agnostic numeric primitives of the dehazing algorithm.

Grouped by concept: the compute backend, patch handling, and the four math
building blocks (airlight, guided filter, transmission, recovery). Nothing here
knows about FITS files, chains, or orchestration.
"""

from .airlight import estimate_airlight, estimate_pairwise_airlight
from .backend import (
    detect_gpu,
    find_nearest_neighbors,
    gaussian_filter_temporal,
    get_array_module,
    is_gpu_free,
    sliding_window_view,
    to_cpu,
    to_gpu,
)
from .guided_filter import guided_filter
from .patches import extract_patches, find_pairs
from .recovery import recover_image
from .transmission import recover_transmission_map

__all__ = [
    # backend
    "get_array_module",
    "to_gpu",
    "to_cpu",
    "sliding_window_view",
    "find_nearest_neighbors",
    "gaussian_filter_temporal",
    "detect_gpu",
    "is_gpu_free",
    # patches
    "extract_patches",
    "find_pairs",
    # math building blocks
    "estimate_airlight",
    "estimate_pairwise_airlight",
    "guided_filter",
    "recover_transmission_map",
    "recover_image",
]
