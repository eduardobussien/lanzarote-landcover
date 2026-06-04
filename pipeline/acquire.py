"""
Data Acquisition via Google Earth Engine
=========================================

Handles querying, filtering, cloud-masking, and annual compositing of
Landsat imagery for the study AOI.

Usage
-----
    import ee
    from pipeline.acquire import initialize_gee, get_annual_composite

    initialize_gee()
    composite_2020 = get_annual_composite(2020)
"""

from __future__ import annotations

import ee

from pipeline.config import (
    AOI_BBOX,
    GEE_PROJECT,
    LANDSAT_COLLECTIONS,
    MAX_CLOUD_COVER_PCT,
    QA_CLOUD_BIT,
    QA_CLOUD_SHADOW_BIT,
    QA_SNOW_BIT,
    SEASON_END_MONTH,
    SEASON_START_MONTH,
    SR_OFFSET,
    SR_SCALE,
)

# ── Initialisation ─────────────────────────────────────────────────────────────

def initialize_gee(project: str = GEE_PROJECT) -> None:
    """
    Initialise the Earth Engine API.
    Credentials must already be saved via `earthengine authenticate`.
    """
    ee.Initialize(project=project)
    print(f"Earth Engine initialised  (project: {project})")


def get_aoi() -> ee.Geometry:
    """Return the study area as a GEE Geometry rectangle."""
    return ee.Geometry.Rectangle(
        [AOI_BBOX["west"], AOI_BBOX["south"], AOI_BBOX["east"], AOI_BBOX["north"]]
    )


# ── Cloud masking ──────────────────────────────────────────────────────────────

def _mask_clouds(image: ee.Image) -> ee.Image:
    """
    Mask cloud, cloud shadow, and snow pixels using the QA_PIXEL band
    (Landsat Collection 2 bit-packed quality layer).
    """
    qa = image.select("QA_PIXEL")

    cloud_mask  = qa.bitwiseAnd(1 << QA_CLOUD_BIT).eq(0)
    shadow_mask = qa.bitwiseAnd(1 << QA_CLOUD_SHADOW_BIT).eq(0)
    snow_mask   = qa.bitwiseAnd(1 << QA_SNOW_BIT).eq(0)

    combined_mask = cloud_mask.And(shadow_mask).And(snow_mask)
    return image.updateMask(combined_mask)


# ── Band renaming & scaling ────────────────────────────────────────────────────

def _rename_and_scale(image: ee.Image, band_map: dict[str, str]) -> ee.Image:
    """
    Rename sensor-specific band names to standardised keys
    ('blue', 'green', 'red', 'nir', 'swir1', 'swir2')
    and apply the Landsat Collection 2 surface reflectance scale factors.
    """
    # Keep only the bands we need (drops thermal, QA, etc.)
    spectral_bands = [v for k, v in band_map.items() if k != "qa"]
    std_names      = [k for k in band_map if k != "qa"]

    scaled = (
        image.select(spectral_bands)
        .rename(std_names)
        .multiply(SR_SCALE)
        .add(SR_OFFSET)
        .clamp(0, 1)                 # reflectance must stay in [0, 1]
    )
    return scaled


# ── Collection loading ─────────────────────────────────────────────────────────

def _best_collection_for_year(year: int) -> str:
    """
    Return the most appropriate Landsat collection ID for a given year,
    preferring later/better sensors when available.

    Landsat timeline:
      1985–1999 → Landsat 5 TM
      1999–2013 → Landsat 7 ETM+  (note: SLC-off from May 2003)
      2013–2021 → Landsat 8 OLI
      2021+     → Landsat 9 OLI-2 (prefer over L8 when available)
    """
    if year >= 2022:
        return "LANDSAT/LC09/C02/T1_L2"
    elif year >= 2013:
        return "LANDSAT/LC08/C02/T1_L2"
    elif year >= 1999:
        return "LANDSAT/LE07/C02/T1_L2"
    else:
        return "LANDSAT/LT05/C02/T1_L2"


def load_collection(year: int, aoi: ee.Geometry | None = None) -> ee.ImageCollection:
    """
    Load, filter, cloud-mask, and scale a Landsat collection for a given year.

    Filters to dry-season months (May–September by default) for consistent
    seasonal compositing across decades.

    Parameters
    ----------
    year : int
        The target year (images from May–September of that year).
    aoi : ee.Geometry, optional
        Area of interest. Defaults to Lanzarote bounding box.

    Returns
    -------
    ee.ImageCollection
        Filtered, cloud-masked, scaled collection ready for compositing.
    """
    if aoi is None:
        aoi = get_aoi()

    collection_id = _best_collection_for_year(year)
    band_map      = LANDSAT_COLLECTIONS[collection_id]

    start_date = f"{year}-{SEASON_START_MONTH:02d}-01"
    end_date   = f"{year}-{SEASON_END_MONTH:02d}-30"

    collection = (
        ee.ImageCollection(collection_id)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUD_COVER", MAX_CLOUD_COVER_PCT))
        .map(_mask_clouds)
        .map(lambda img: _rename_and_scale(img, band_map))
    )

    return collection


# ── Annual compositing ─────────────────────────────────────────────────────────

def get_annual_composite(
    year: int,
    aoi: ee.Geometry | None = None,
    method: str = "median",
) -> ee.Image:
    """
    Create an annual dry-season composite for a given year.

    Per-pixel median compositing is used by default - robust against
    remaining cloud/shadow artefacts, and represents typical conditions
    rather than single-scene outliers.

    Parameters
    ----------
    year : int
    aoi : ee.Geometry, optional
    method : str
        Compositing method: 'median' (default) or 'mosaic' (most recent pixel).

    Returns
    -------
    ee.Image
        Composite with bands: blue, green, red, nir, swir1, swir2.
        Returns None equivalent (empty image) if no scenes are available.
    """
    if aoi is None:
        aoi = get_aoi()

    collection = load_collection(year, aoi)

    if method == "median":
        composite = collection.median()
    elif method == "mosaic":
        composite = collection.mosaic()
    else:
        raise ValueError(f"Unknown compositing method: {method!r}. Use 'median' or 'mosaic'.")

    return composite.clip(aoi).set("year", year)


def get_composite_series(
    start_year: int,
    end_year: int,
    aoi: ee.Geometry | None = None,
    step: int = 1,
) -> list[ee.Image]:
    """
    Create annual composites for a range of years.

    Parameters
    ----------
    start_year, end_year : int
    aoi : ee.Geometry, optional
    step : int
        Year step (e.g. step=5 gives decadal composites).

    Returns
    -------
    list of ee.Image
    """
    return [
        get_annual_composite(year, aoi)
        for year in range(start_year, end_year + 1, step)
    ]


# ── Scene count diagnostics ────────────────────────────────────────────────────

def scene_count(year: int, aoi: ee.Geometry | None = None) -> int:
    """
    Return the number of cloud-filtered scenes available for a given year.
    Useful for checking data coverage before compositing.
    """
    if aoi is None:
        aoi = get_aoi()
    collection = load_collection(year, aoi)
    return collection.size().getInfo()
