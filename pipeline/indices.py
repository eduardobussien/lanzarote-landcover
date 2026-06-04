"""
Spectral Index Calculations
============================

Two interfaces:
  - numpy_*  functions  → operate on local numpy arrays (after GeoTIFF download)
  - gee_*    functions  → operate on ee.Image objects (server-side GEE processing)

All numpy functions expect float32 arrays with values in [0, 1] surface reflectance.
A small epsilon (1e-10) is added to denominators to prevent division by zero.
"""

import numpy as np

# ── NumPy interface ────────────────────────────────────────────────────────────

_EPS = 1e-10   # division-by-zero guard


def ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """
    Normalized Difference Vegetation Index.
    Measures vegetation health / density.

    Range: -1 to 1
      Forest   :  0.6 – 0.9
      Crops    :  0.3 – 0.6
      Urban    : -0.1 – 0.1
      Water    : < -0.1
      Volcanic :  0.0 – 0.05  (dark basalt gives near-zero)
    """
    return (nir - red) / (nir + red + _EPS)


def ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """
    Normalized Difference Water Index (McFeeters 1996).
    Highlights open water bodies. Positive values indicate water.
    """
    return (green - nir) / (green + nir + _EPS)


def ndbi(swir1: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """
    Normalized Difference Built-up Index.
    Highlights impervious/built-up surfaces. Positive values = urban.

    Note for Lanzarote: dark basalt (Barren/Volcanic) can also have
    positive NDBI - combine with NDVI and elevation to disambiguate.
    """
    return (swir1 - nir) / (swir1 + nir + _EPS)


def savi(nir: np.ndarray, red: np.ndarray, L: float = 0.5) -> np.ndarray:
    """
    Soil-Adjusted Vegetation Index (Huete 1988).
    Better than NDVI in areas with sparse vegetation and exposed soil -
    critical for Lanzarote and Fuerteventura where soil background is dominant.

    L = 0.5  is the standard soil brightness correction factor.
    """
    return ((nir - red) / (nir + red + L + _EPS)) * (1 + L)


def bsi(swir1: np.ndarray, red: np.ndarray,
        nir: np.ndarray, blue: np.ndarray) -> np.ndarray:
    """
    Bare Soil Index.
    Identifies exposed soil, volcanic rock, desert surfaces, and construction sites.
    High values on Lanzarote's malpais lava fields and Fuerteventura's dunes.
    """
    return ((swir1 + red) - (nir + blue)) / ((swir1 + red) + (nir + blue) + _EPS)


def evi(nir: np.ndarray, red: np.ndarray, blue: np.ndarray) -> np.ndarray:
    """
    Enhanced Vegetation Index (Liu & Huete 1995).
    More sensitive than NDVI in high-biomass areas; corrects for
    atmospheric effects and soil background.

    Calibrated for Landsat surface reflectance.
    """
    return 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1 + _EPS)


def mndwi(green: np.ndarray, swir1: np.ndarray) -> np.ndarray:
    """
    Modified Normalized Difference Water Index (Xu 2006).
    More effective than NDWI for distinguishing water from built-up areas
    since SWIR is absorbed by water but reflected by urban surfaces.
    """
    return (green - swir1) / (green + swir1 + _EPS)


def calculate_all(bands: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """
    Compute all indices from a bands dictionary.

    Parameters
    ----------
    bands : dict with keys 'blue', 'green', 'red', 'nir', 'swir1', 'swir2'
            Values should be float32 surface reflectance arrays (0–1 range).

    Returns
    -------
    dict mapping index name → numpy array of same spatial shape as input.
    """
    return {
        "ndvi":  ndvi(bands["nir"], bands["red"]),
        "ndwi":  ndwi(bands["green"], bands["nir"]),
        "ndbi":  ndbi(bands["swir1"], bands["nir"]),
        "savi":  savi(bands["nir"], bands["red"]),
        "bsi":   bsi(bands["swir1"], bands["red"], bands["nir"], bands["blue"]),
        "evi":   evi(bands["nir"], bands["red"], bands["blue"]),
        "mndwi": mndwi(bands["green"], bands["swir1"]),
    }


# ── Google Earth Engine interface ─────────────────────────────────────────────
# These functions accept and return ee.Image objects for server-side processing.

def gee_add_indices(image):
    """
    Add all spectral indices as new bands to a GEE ee.Image.
    Input image must already have bands renamed to:
      'blue', 'green', 'red', 'nir', 'swir1', 'swir2'

    Returns the image with 7 additional bands:
      ndvi, ndwi, ndbi, savi, bsi, evi, mndwi
    """
    try:
        import ee
    except ImportError as exc:
        raise ImportError("earthengine-api is required for GEE functions") from exc

    ndvi_img = image.normalizedDifference(["nir", "red"]).rename("ndvi")

    ndwi_img = image.normalizedDifference(["green", "nir"]).rename("ndwi")

    ndbi_img = image.normalizedDifference(["swir1", "nir"]).rename("ndbi")

    savi_img = (
        image.expression(
            "((NIR - RED) / (NIR + RED + 0.5)) * 1.5",
            {"NIR": image.select("nir"), "RED": image.select("red")},
        ).rename("savi")
    )

    bsi_img = (
        image.expression(
            "((SWIR1 + RED) - (NIR + BLUE)) / ((SWIR1 + RED) + (NIR + BLUE))",
            {
                "SWIR1": image.select("swir1"),
                "RED":   image.select("red"),
                "NIR":   image.select("nir"),
                "BLUE":  image.select("blue"),
            },
        ).rename("bsi")
    )

    evi_img = (
        image.expression(
            "2.5 * (NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1)",
            {
                "NIR":  image.select("nir"),
                "RED":  image.select("red"),
                "BLUE": image.select("blue"),
            },
        ).rename("evi")
    )

    mndwi_img = image.normalizedDifference(["green", "swir1"]).rename("mndwi")

    return image.addBands([ndvi_img, ndwi_img, ndbi_img, savi_img,
                           bsi_img, evi_img, mndwi_img])
