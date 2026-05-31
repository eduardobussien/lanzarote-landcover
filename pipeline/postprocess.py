"""
Post-processing
================

Cleans up classifier output:
  - Majority filter (removes salt-and-pepper noise)
  - Minimum mapping unit filter (removes tiny isolated patches)
  - Sieve filter (connects fragmented areas of the same class)

The 3x3 majority filter is applied by default. A 5x5 window can be used
in arid areas (Lanzarote, Fuerteventura) where the landscape is more
homogeneous and small patches are likely classification noise.
"""

# TODO (Phase 2): Implement post-processing with scipy.ndimage

import numpy as np


def majority_filter(classified: np.ndarray, window: int = 3) -> np.ndarray:
    """
    Replace each pixel with the most common class in its neighbourhood.
    Removes isolated 'salt-and-pepper' misclassifications.

    Parameters
    ----------
    classified : 2D int array
    window : int
        Size of the square neighbourhood (3 or 5 recommended).
    """
    raise NotImplementedError("Phase 2")


def minimum_mapping_unit(classified: np.ndarray, min_pixels: int = 9) -> np.ndarray:
    """
    Remove patches smaller than min_pixels (default = 9 pixels = ~0.08 km²
    at 30m resolution). Assign them to the dominant surrounding class.
    """
    raise NotImplementedError("Phase 2")
