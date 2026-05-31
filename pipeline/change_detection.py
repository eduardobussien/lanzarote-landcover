"""
Change Detection & Area Statistics
====================================

Computes:
  - Transition matrices between any two classified years
  - Area time series (km²) per class across all years
  - Net change per class (gain / loss)
  - Rate of change and trend significance
  - Change hotspot maps (pixels that changed at least once)

Key events to validate against (Canary Islands ground truth):
  - 2021 Cumbre Vieja eruption on La Palma → new Barren/Volcanic land
  - Gran Canaria wildfire 2019 → vegetation loss then recovery
  - Tenerife wildfire 2023
  - Southern Tenerife resort expansion 1985–2010
"""

# TODO (Phase 3): Implement change detection

import numpy as np
from pipeline.config import CLASS_NAMES, N_CLASSES, PIXEL_AREA_M2


def compute_change_matrix(map_t1: np.ndarray, map_t2: np.ndarray) -> np.ndarray:
    """
    Transition matrix: rows = from class, cols = to class.
    Cell (i, j) = number of pixels that changed from class i → class j.
    Diagonal = pixels that stayed the same class (no change).

    Returns np.ndarray of shape (N_CLASSES, N_CLASSES), dtype int64.
    """
    raise NotImplementedError("Phase 3")


def compute_area_timeseries(
    classified_maps: dict[int, np.ndarray],
) -> dict[int, dict[str, float]]:
    """
    For each year, compute total area (km²) per land cover class.

    Parameters
    ----------
    classified_maps : dict mapping year → classified raster (2D int array)

    Returns
    -------
    dict mapping year → {class_name: area_km2}
    """
    raise NotImplementedError("Phase 3")


def net_change(
    timeseries: dict[int, dict[str, float]],
    start_year: int,
    end_year: int,
) -> dict[str, float]:
    """
    Net change in km² per class between two years.
    Positive = gain, negative = loss.
    """
    raise NotImplementedError("Phase 3")


def change_hotspots(classified_maps: dict[int, np.ndarray]) -> np.ndarray:
    """
    Return a binary mask highlighting pixels that changed class at least once
    across the full time series. Shape matches the input rasters.
    """
    raise NotImplementedError("Phase 3")
