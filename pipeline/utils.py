"""
Shared Utilities
=================

Helpers for I/O, logging, CRS checks, and array manipulation
used across the pipeline.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from pipeline.config import CLASSIFIED_DIR, CRS_EPSG

logger = logging.getLogger(__name__)


# ── Logging ────────────────────────────────────────────────────────────────────

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a pre-configured logger."""
    logging.basicConfig(
        format="%(asctime)s  %(levelname)-8s  %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    log = logging.getLogger(name)
    log.setLevel(level)
    return log


# ── File I/O ───────────────────────────────────────────────────────────────────

def ensure_dir(path: str | Path) -> Path:
    """Create a directory (and parents) if it does not exist. Return the Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def classified_path(year: int) -> Path:
    """Return the expected output path for a classified raster year."""
    return CLASSIFIED_DIR / f"classified_{year}.tif"


# ── Array utilities ────────────────────────────────────────────────────────────

def stack_bands(bands: dict[str, np.ndarray]) -> np.ndarray:
    """
    Stack a dict of 2D arrays into a single 3D array (bands, height, width).
    Order follows the dict insertion order.
    """
    return np.stack(list(bands.values()), axis=0)


def unstack_bands(array: np.ndarray, names: list[str]) -> dict[str, np.ndarray]:
    """Inverse of stack_bands - split a (bands, H, W) array into a named dict."""
    assert array.shape[0] == len(names), "Band count must match names list length"
    return {name: array[i] for i, name in enumerate(names)}


def pixel_to_km2(pixel_count: int, pixel_area_m2: float = 900.0) -> float:
    """Convert a pixel count to area in km²."""
    return (pixel_count * pixel_area_m2) / 1_000_000


# ── GEE helpers ───────────────────────────────────────────────────────────────

def check_gee_initialized() -> bool:
    """Return True if Earth Engine has been initialised in this session."""
    try:
        import ee
        ee.Number(1).getInfo()   # cheap server-side call
        return True
    except Exception:
        return False
