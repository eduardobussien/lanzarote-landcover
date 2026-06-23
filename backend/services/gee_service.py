"""GEE service: lazy initialization, classifier training, and tile URL generation.

The first call to get_tile_url() for any year:
  1. Initializes the EE session (picks up credentials from ~/.config/earthengine/credentials)
  2. Trains the Random Forest classifier on a 2023 composite + CORINE labels
  3. Classifies the requested year and returns a Leaflet-compatible XYZ tile URL

Subsequent calls for the same year return a cached URL instantly.
Subsequent calls for different years skip steps 1 and 2 (~5-15 s per year).
"""

import threading

from pipeline.config import (
    AOI_BBOX,
    CORINE_REMAP,
    GEE_PROJECT,
    QA_CLOUD_BIT,
    QA_CLOUD_SHADOW_BIT,
    SR_OFFSET,
    SR_SCALE,
)
from pipeline.indices import gee_add_indices

ACTIVE_CLASSES = [0, 2, 3, 4]   # Urban, Water, Agriculture, Barren
FEATURE_BANDS = [
    "blue", "green", "red", "nir", "swir1", "swir2",
    "ndvi", "ndwi", "ndbi", "savi", "bsi", "evi", "mndwi",
]

# Full 6-class palette - indices 1 (Forest) and 5 (Shrubland) are absent on Lanzarote
CLASS_PALETTE = [
    "#E8443A",   # 0 Urban/Built-up
    "#2D8C3C",   # 1 Forest/Woodland
    "#3B82F6",   # 2 Water/Wetland
    "#F5C542",   # 3 Agriculture
    "#4A4A4A",   # 4 Barren/Volcanic
    "#C4A86B",   # 5 Shrubland/Matorral
]
VIS_PARAMS = {"min": 0, "max": 5, "palette": CLASS_PALETTE}

_lock = threading.Lock()
_ready = False
_aoi = None
_classifier = None
_land_mask = None
_tile_url_cache: dict[int, str] = {}


def _ensure_ready() -> None:
    global _ready, _aoi, _classifier, _land_mask
    if _ready:
        return
    with _lock:
        if _ready:
            return
        import ee  # lazy import - not needed until a tile is actually requested
        ee.Initialize(project=GEE_PROJECT)
        _aoi = ee.Geometry.Rectangle([
            AOI_BBOX["west"], AOI_BBOX["south"],
            AOI_BBOX["east"], AOI_BBOX["north"],
        ])

        from_vals = list(CORINE_REMAP.keys())
        to_vals   = list(CORINE_REMAP.values())
        corine_raw      = ee.Image("COPERNICUS/CORINE/V20/100m/2018").select("landcover").clip(_aoi)
        corine_remapped = corine_raw.remap(from_vals, to_vals, defaultValue=-1).rename("label")
        corine_labels   = corine_remapped.updateMask(corine_remapped.gte(0))
        _land_mask      = corine_labels.mask()

        comp_ref = _make_composite(2023)
        training = comp_ref.select(FEATURE_BANDS).addBands(corine_labels)
        samples = training.stratifiedSample(
            numPoints   = 750,
            classBand   = "label",
            region      = _aoi,
            scale       = 100,
            classValues = ACTIVE_CLASSES,
            classPoints = [750] * len(ACTIVE_CLASSES),
            seed        = 42,
            geometries  = False,
        )
        _classifier = ee.Classifier.smileRandomForest(
            numberOfTrees=200, seed=42
        ).train(
            features        = samples,
            classProperty   = "label",
            inputProperties = FEATURE_BANDS,
        )
        _ready = True


def _make_composite(year: int):
    import ee  # noqa: PLC0415
    if year >= 2022:
        col_id = "LANDSAT/LC09/C02/T1_L2"
        b_in   = ["SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"]
    elif year >= 2013:
        col_id = "LANDSAT/LC08/C02/T1_L2"
        b_in   = ["SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"]
    elif year >= 1999:
        col_id = "LANDSAT/LE07/C02/T1_L2"
        b_in   = ["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B7"]
    else:
        col_id = "LANDSAT/LT05/C02/T1_L2"
        b_in   = ["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B7"]
    b_out = ["blue", "green", "red", "nir", "swir1", "swir2"]

    def mask_clouds(img):
        qa = img.select("QA_PIXEL")
        return img.updateMask(
            qa.bitwiseAnd(1 << QA_CLOUD_BIT).eq(0).And(
                qa.bitwiseAnd(1 << QA_CLOUD_SHADOW_BIT).eq(0)
            )
        )

    def scale_sr(img):
        return img.addBands(
            img.select("SR_B.").multiply(SR_SCALE).add(SR_OFFSET),
            overwrite=True,
        )

    composite = (
        ee.ImageCollection(col_id)
        .filterBounds(_aoi)
        .filterDate(f"{year}-05-01", f"{year}-09-30")
        .filter(ee.Filter.lt("CLOUD_COVER", 80))
        .map(mask_clouds)
        .map(scale_sr)
        .select(b_in, b_out)
        .median()
        .clip(_aoi)
    )
    return gee_add_indices(composite)


def get_tile_url(year: int) -> str:
    """Return a Leaflet-compatible XYZ tile URL for the classified map of *year*."""
    if year in _tile_url_cache:
        return _tile_url_cache[year]
    _ensure_ready()
    composite = _make_composite(year)
    classified = (
        composite.select(FEATURE_BANDS)
        .classify(_classifier)
        .rename("classification")
        .updateMask(_land_mask)
        .toInt()
        .clip(_aoi)
    )
    url = classified.getMapId(VIS_PARAMS)["tile_fetcher"].url_format
    _tile_url_cache[year] = url
    return url
