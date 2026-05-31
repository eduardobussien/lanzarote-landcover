"""
Preprocessing Pipeline
=======================

Handles local raster preprocessing after scenes have been downloaded:
  - Reprojection to EPSG:32628 (UTM zone 28N)
  - Clipping to AOI
  - Cloud masking (QA_PIXEL bit unpacking)
  - Spectral index calculation
  - Reflectance normalisation
  - Annual median compositing

Note: When using Google Earth Engine (Phase 1), most of these steps happen
server-side in acquire.py. This module is for local GeoTIFF processing
in Phase 2 when working with downloaded scenes.
"""

# TODO (Phase 2): Implement local preprocessing with rasterio/GDAL
# Reference: pipeline/acquire.py for the GEE equivalent of each step

import numpy as np


def reproject_to_utm(src_path: str, dst_path: str) -> None:
    """Reproject a GeoTIFF to EPSG:32628 (UTM zone 28N)."""
    raise NotImplementedError("Phase 2")


def clip_to_aoi(src_path: str, dst_path: str, aoi_geojson: dict) -> None:
    """Clip a raster to the AOI polygon."""
    raise NotImplementedError("Phase 2")


def apply_cloud_mask(band_array: np.ndarray, qa_array: np.ndarray) -> np.ndarray:
    """
    Set cloud/shadow pixels to NaN using QA_PIXEL bit flags.
    Returns masked array of same shape.
    """
    raise NotImplementedError("Phase 2")


def normalize_reflectance(array: np.ndarray) -> np.ndarray:
    """Scale raw Landsat Collection 2 DN values to [0, 1] surface reflectance."""
    raise NotImplementedError("Phase 2")


def create_annual_composite(scene_arrays: list[np.ndarray]) -> np.ndarray:
    """
    Per-pixel median composite across multiple scenes within a year.
    NaN values (masked pixels) are ignored in the median calculation.
    """
    raise NotImplementedError("Phase 2")
