"""GEE service: per-sensor classifiers and tile URL generation.

Why per-sensor classifiers
---------------------------
Landsat 5, 7, 8 and 9 measure the same physical surfaces with slightly
different spectral responses. A single Random Forest trained on modern
Landsat 8/9 imagery misclassifies older Landsat 5 scenes - on Lanzarote,
enarenado farmland ends up flagged as Urban. That produced the nonsensical
result of 1990 showing MORE urban area than 2023.

The fix: train one classifier per sensor generation, each paired with the
CORINE reference map closest to that era. Each classifier then only ever sees
imagery from the sensor family it learned from.

Two classifiers cover the whole study period (display years 2005-2023):

    TM/ETM+ era  -> years <= 2012   (Landsat 5 + 7, trained on CORINE 2006)
    OLI era      -> years >= 2013   (Landsat 8 + 9, trained on CORINE 2018)

Each era merges the two collections that share its band layout (Landsat 5 + 7
for TM/ETM+, Landsat 8 + 9 for OLI). Merging Landsat 7 into the older era fills
the gap when Landsat 5 acquisitions were reduced (1999-2003); Landsat 7's
SLC-off gaps after 2003 are partly filled by the median composite.

Concurrency: initialization and per-sensor classifier training are guarded by
locks so each happens once, but the blocking GEE calls (getMapId, getInfo) run
WITHOUT holding a lock, so concurrent tile/area requests proceed in parallel.
The first request per sensor still pays the ~30-60 s training cost server-side;
results are cached per year thereafter.
"""

import threading

from pipeline.config import (
    AOI_BBOX,
    CORINE_REMAP,
    CRS_EPSG_INT,
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
BANDS_OUT = ["blue", "green", "red", "nir", "swir1", "swir2"]

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

# Classifier output index -> display name (only the 4 active classes appear).
CLASS_INDEX_TO_NAME = {
    0: "Urban/Built-up",
    2: "Water/Wetland",
    3: "Agriculture",
    4: "Barren/Volcanic",
}
# One Landsat pixel is 30 x 30 m = 900 m2 = 0.0009 km2.
KM2_PER_PIXEL = 0.0009

# Per-classifier configuration. Each classifier is trained on a composite from
# its own sensor generation, paired with the CORINE reference map closest to
# that era. Training uses a multi-year window (an "epochal composite") so a
# single year's sparse coverage or cloud gaps can never produce an empty image.
#
# Each era draws from MULTIPLE collections that share band layouts and were
# designed for spectral continuity:
#   - TM/ETM+ era (<= 2012): Landsat 5 + Landsat 7 (identical SR_B1..SR_B7).
#     Landsat 5 acquisitions were reduced 1999-2003 while Landsat 7 was primary,
#     so merging the two fills that gap (e.g. the 2002 map).
#   - OLI era (>= 2013): Landsat 8 + Landsat 9 (identical SR_B2..SR_B7).
TM_BANDS  = ["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B7"]
OLI_BANDS = ["SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"]

SENSOR_CONFIG = {
    "L5": {
        "sources": [
            ("LANDSAT/LT05/C02/T1_L2", TM_BANDS),
            ("LANDSAT/LE07/C02/T1_L2", TM_BANDS),
        ],
        "corine":      "COPERNICUS/CORINE/V20/100m/2006",
        "train_start": 2004,
        "train_end":   2008,
    },
    "L8": {
        "sources": [
            ("LANDSAT/LC08/C02/T1_L2", OLI_BANDS),
            ("LANDSAT/LC09/C02/T1_L2", OLI_BANDS),
        ],
        "corine":      "COPERNICUS/CORINE/V20/100m/2018",
        "train_start": 2016,
        "train_end":   2020,
    },
}

# Half-width (in years) of the window used to build each display year's map.
# "1990" therefore means a circa-1989-1991 dry-season composite, which avoids
# empty images when a single year has no usable Landsat scenes.
CLASSIFY_HALF_WINDOW = 1

# Locks guard only the one-time setup and per-sensor training (cheap graph
# building + shared-state writes). The blocking GEE network calls run OUTSIDE
# any lock so concurrent requests are not serialized.
_init_lock = threading.Lock()
_classifier_locks = {"L5": threading.Lock(), "L8": threading.Lock()}

_initialized = False
_aoi = None
_land_mask = None
_classifiers: dict = {}                  # sensor_key -> trained ee.Classifier
_tile_url_cache: dict[int, str] = {}
_area_cache: dict[int, dict] = {}        # year -> {class_name: area_km2}
_change_cache: dict[tuple, dict] = {}    # (year_a, year_b) -> change map + stats


def _sensor_for_year(year: int) -> str:
    """Pick the sensor family used to image (and classify) a given year."""
    return "L8" if year >= 2013 else "L5"


def _init_base() -> None:
    """Initialize EE, the AOI, and the coastline land mask (once, thread-safe)."""
    global _initialized, _aoi, _land_mask
    if _initialized:
        return
    with _init_lock:
        if _initialized:                 # re-check inside the lock
            return
        import ee  # lazy import - not needed until a tile is actually requested
        ee.Initialize(project=GEE_PROJECT)
        _aoi = ee.Geometry.Rectangle([
            AOI_BBOX["west"], AOI_BBOX["south"],
            AOI_BBOX["east"], AOI_BBOX["north"],
        ])
        # Land mask from CORINE 2018 land extent - the coastline is stable
        # enough to use one mask for every year, keeping ocean out of the maps.
        from_vals = list(CORINE_REMAP.keys())
        to_vals   = list(CORINE_REMAP.values())
        corine    = ee.Image("COPERNICUS/CORINE/V20/100m/2018").select("landcover").clip(_aoi)
        remapped  = corine.remap(from_vals, to_vals, defaultValue=-1)
        labels    = remapped.updateMask(remapped.gte(0))
        _land_mask = labels.mask()
        _initialized = True              # set last: readers that see True see a ready state


def _composite(sensor_key: str, year_start: int, year_end: int):
    """Cloud-masked, scaled, dry-season median composite for one sensor.

    Aggregates every dry-season (May-Sep) scene from *year_start* to *year_end*
    inclusive. Spanning multiple years guarantees enough valid pixels even when
    an individual year has sparse coverage or heavy cloud.
    """
    import ee  # noqa: PLC0415
    cfg = SENSOR_CONFIG[sensor_key]

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

    def prep(collection_id, bands_in):
        return (
            ee.ImageCollection(collection_id)
            .filterBounds(_aoi)
            .filterDate(f"{year_start}-01-01", f"{year_end}-12-31")
            # Keep only dry-season months across the whole multi-year span.
            .filter(ee.Filter.calendarRange(5, 9, "month"))
            .filter(ee.Filter.lt("CLOUD_COVER", 80))
            .map(mask_clouds)
            .map(scale_sr)
            .select(bands_in, BANDS_OUT)
        )

    # Merge every source collection for this era into one collection, then
    # take the per-pixel median across all dry-season scenes.
    merged = None
    for collection_id, bands_in in cfg["sources"]:
        c = prep(collection_id, bands_in)
        merged = c if merged is None else merged.merge(c)

    composite = merged.median().clip(_aoi)
    return gee_add_indices(composite)


def _get_classifier(sensor_key: str):
    """Lazily build and cache the Random Forest for one sensor family.

    Guarded by a per-sensor lock so the (cheap, client-side) graph is built
    once. The lock is not held during any network call. Building the L5 and L8
    classifiers uses separate locks, so they never block each other.
    """
    if sensor_key in _classifiers:
        return _classifiers[sensor_key]

    with _classifier_locks[sensor_key]:
        if sensor_key in _classifiers:       # re-check inside the lock
            return _classifiers[sensor_key]

        import ee  # noqa: PLC0415
        cfg = SENSOR_CONFIG[sensor_key]

        # Era-matched CORINE labels for this sensor.
        from_vals = list(CORINE_REMAP.keys())
        to_vals   = list(CORINE_REMAP.values())
        corine    = ee.Image(cfg["corine"]).select("landcover").clip(_aoi)
        remapped  = corine.remap(from_vals, to_vals, defaultValue=-1).rename("label")
        labels    = remapped.updateMask(remapped.gte(0))

        # Training composite from THIS sensor, over its multi-year reference window.
        comp     = _composite(sensor_key, cfg["train_start"], cfg["train_end"])
        training = comp.select(FEATURE_BANDS).addBands(labels)

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
        classifier = ee.Classifier.smileRandomForest(
            numberOfTrees=200, seed=42
        ).train(
            features        = samples,
            classProperty   = "label",
            inputProperties = FEATURE_BANDS,
        )
        _classifiers[sensor_key] = classifier
        return classifier


def _classified_image(year: int):
    """Build the classified land-cover image graph for *year*.

    Pure client-side graph building - no network. `_init_base` and
    `_get_classifier` do their own internal locking; nothing here needs a lock.
    """
    _init_base()
    sensor_key = _sensor_for_year(year)
    classifier = _get_classifier(sensor_key)
    composite  = _composite(
        sensor_key,
        year - CLASSIFY_HALF_WINDOW,
        year + CLASSIFY_HALF_WINDOW,
    )
    return (
        composite.select(FEATURE_BANDS)
        .classify(classifier)
        .rename("classification")
        .updateMask(_land_mask)
        .toInt()
        .clip(_aoi)
    )


def get_tile_url(year: int) -> str:
    """Return a Leaflet-compatible XYZ tile URL for the classified map of *year*.

    Building the image graph runs init/training under their own locks; the
    blocking getMapId call runs unlocked so concurrent requests do not serialize.
    """
    if year in _tile_url_cache:
        return _tile_url_cache[year]

    classified = _classified_image(year)
    url = classified.getMapId(VIS_PARAMS)["tile_fetcher"].url_format
    _tile_url_cache[year] = url          # dict write is atomic; a rare double compute is harmless
    return url


def get_class_areas(year: int) -> dict:
    """Return {class_name: area_km2} for *year*, from the same live classification.

    Uses a frequency histogram of the classified pixels so the numbers always
    match exactly what the map shows for that year. The blocking getInfo call
    runs unlocked so concurrent requests do not serialize.
    """
    if year in _area_cache:
        return _area_cache[year]

    import ee  # noqa: PLC0415
    classified = _classified_image(year)
    hist = classified.reduceRegion(
        reducer   = ee.Reducer.frequencyHistogram(),
        geometry  = _aoi,
        scale     = 30,
        crs       = f"EPSG:{CRS_EPSG_INT}",   # UTM 28N, so each pixel is exactly 900 m2
        maxPixels = int(1e10),
    ).get("classification")
    hist = ee.Dictionary(hist).getInfo() or {}

    areas: dict[str, float] = {}
    for key, count in hist.items():
        name = CLASS_INDEX_TO_NAME.get(int(float(key)))
        if name:
            areas[name] = round(count * KM2_PER_PIXEL, 1)

    # Don't cache an empty result - a transient blip or an unservable year would
    # otherwise report 0 km2 forever. Let the caller surface it as an error.
    if not areas:
        raise ValueError(
            f"No classified land pixels for {year} - no usable imagery in the window"
        )

    _area_cache[year] = areas
    return areas


def get_change_map(year_a: int, year_b: int) -> dict:
    """Compare two years and return a change map + how much land changed class.

    The map shows ONLY the pixels whose class differs between the two years,
    coloured by the class they BECAME in year_b (unchanged pixels are
    transparent). Because both years use the same sensor and classifier, the
    difference reflects real land cover change rather than a change of method.
    """
    key = (year_a, year_b)
    if key in _change_cache:
        return _change_cache[key]

    import ee  # noqa: PLC0415
    a = _classified_image(year_a)
    b = _classified_image(year_b)

    changed = a.neq(b).rename("changed")          # 1 where the class differs (land only)
    change_img = b.updateMask(changed)            # keep only changed pixels, coloured by new class
    url = change_img.getMapId(VIS_PARAMS)["tile_fetcher"].url_format

    # One call for both the changed-pixel count and the total land-pixel count.
    stats_img = changed.addBands(a.mask().rename("land"))
    stats = stats_img.reduceRegion(
        reducer   = ee.Reducer.sum(),
        geometry  = _aoi,
        scale     = 30,
        crs       = f"EPSG:{CRS_EPSG_INT}",
        maxPixels = int(1e10),
    ).getInfo() or {}

    changed_px = stats.get("changed") or 0
    land_px    = stats.get("land") or 0
    result = {
        "tile_url":    url,
        "changed_km2": round(changed_px * KM2_PER_PIXEL, 1),
        "changed_pct": round(changed_px / land_px * 100, 1) if land_px else 0.0,
    }
    _change_cache[key] = result
    return result
