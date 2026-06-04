"""
Central configuration for the Lanzarote Land Cover pipeline.

Edit GEE_PROJECT to match your Google Earth Engine / Cloud project ID.
Everything else is tuned for Lanzarote + dry-season Landsat compositing.
"""

from pathlib import Path

# ── Google Earth Engine ────────────────────────────────────────────────────────
GEE_PROJECT = "project-4cb2ec4e-f113-48f1-8b5"

# ── Study Area ─────────────────────────────────────────────────────────────────
# Lanzarote + La Graciosa bounding box (WGS-84 / EPSG:4326)
AOI_BBOX = {
    "west":  -13.92,
    "south":  28.80,
    "east":  -13.30,
    "north":  29.30,
}

# Projected CRS for the Canary Islands (WGS 84 / UTM zone 28N)
CRS_EPSG     = "EPSG:32628"
CRS_EPSG_INT = 32628
PIXEL_SIZE_M = 30                       # Landsat native resolution (metres)
PIXEL_AREA_M2 = PIXEL_SIZE_M ** 2      # 900 m²

# ── Time range ─────────────────────────────────────────────────────────────────
YEAR_START = 1985
YEAR_END   = 2024

# Dry-season months (May–September) - consistent seasonality, no wet-season bias
SEASON_START_MONTH = 5   # May
SEASON_END_MONTH   = 9   # September

# ── Land Cover Classes ─────────────────────────────────────────────────────────
CLASS_NAMES = [
    "Urban/Built-up",
    "Forest/Woodland",
    "Water/Wetland",
    "Agriculture",
    "Barren/Volcanic",
    "Shrubland/Matorral",
]

CLASS_COLORS = {
    "Urban/Built-up":     "#E8443A",   # red
    "Forest/Woodland":    "#2D8C3C",   # dark green
    "Water/Wetland":      "#3B82F6",   # blue
    "Agriculture":        "#F5C542",   # golden yellow
    "Barren/Volcanic":    "#4A4A4A",   # dark grey (matches basalt)
    "Shrubland/Matorral": "#C4A86B",   # olive tan
}

CLASS_LABELS    = {name: i for i, name in enumerate(CLASS_NAMES)}
LABEL_TO_CLASS  = {i: name for i, name in enumerate(CLASS_NAMES)}
N_CLASSES       = len(CLASS_NAMES)

# ── CORINE → simplified class mapping ──────────────────────────────────────────
# Keys are CORINE Level-3 integer codes; values are our class indices above.
CORINE_REMAP: dict[int, int] = {
    # 0 - Urban/Built-up  (CORINE artificial surfaces 111–142)
    **{code: 0 for code in range(111, 143)},
    # 1 - Forest/Woodland  (311 broadleaved, 312 coniferous, 313 mixed)
    **{code: 1 for code in [311, 312, 313]},
    # 2 - Water/Wetland  (inland wetlands 411-423, coastal lagoons 521-522)
    # 523 (Sea and ocean) intentionally excluded - avoids sampling open ocean pixels
    # when the AOI bounding box extends beyond the island coastline.
    **{code: 2 for code in [411, 412, 421, 422, 423, 511, 512, 521, 522]},
    # 3 - Agriculture  (arable land 211-213, permanent crops 221-244)
    **{code: 3 for code in range(211, 245)},
    # 4 - Barren/Volcanic  (bare rock 332, sand 331, burnt 334, glaciers 335)
    **{code: 4 for code in [331, 332, 333, 334, 335]},
    # 5 - Shrubland/Matorral  (natural grassland 321, moors 322, sclerophyllous 323, transitional 324)
    **{code: 5 for code in [321, 322, 323, 324]},
}

# ── Landsat Collection 2 Level-2 - band names by sensor ───────────────────────
# All sensors map to the same standardised keys used throughout the pipeline.
LANDSAT_COLLECTIONS = {
    "LANDSAT/LT05/C02/T1_L2": {   # Landsat 5 TM (1984–2013)
        "blue":  "SR_B1",
        "green": "SR_B2",
        "red":   "SR_B3",
        "nir":   "SR_B4",
        "swir1": "SR_B5",
        "swir2": "SR_B7",
        "qa":    "QA_PIXEL",
    },
    "LANDSAT/LE07/C02/T1_L2": {   # Landsat 7 ETM+ (1999–present)
        "blue":  "SR_B1",
        "green": "SR_B2",
        "red":   "SR_B3",
        "nir":   "SR_B4",
        "swir1": "SR_B5",
        "swir2": "SR_B7",
        "qa":    "QA_PIXEL",
    },
    "LANDSAT/LC08/C02/T1_L2": {   # Landsat 8 OLI (2013–present)
        "blue":  "SR_B2",
        "green": "SR_B3",
        "red":   "SR_B4",
        "nir":   "SR_B5",
        "swir1": "SR_B6",
        "swir2": "SR_B7",
        "qa":    "QA_PIXEL",
    },
    "LANDSAT/LC09/C02/T1_L2": {   # Landsat 9 OLI-2 (2021–present)
        "blue":  "SR_B2",
        "green": "SR_B3",
        "red":   "SR_B4",
        "nir":   "SR_B5",
        "swir1": "SR_B6",
        "swir2": "SR_B7",
        "qa":    "QA_PIXEL",
    },
}

# Surface reflectance scale factors (Landsat Collection 2 Level-2)
SR_SCALE  = 0.0000275
SR_OFFSET = -0.2

# QA_PIXEL bit positions (Landsat Collection 2)
QA_CLOUD_BIT        = 3   # Cloud
QA_CLOUD_SHADOW_BIT = 4   # Cloud shadow
QA_SNOW_BIT         = 5   # Snow/ice (rare on Lanzarote but handled)

# ── Cloud / quality thresholds ─────────────────────────────────────────────────
MAX_CLOUD_COVER_PCT = 20   # Discard scenes with >20% cloud cover

# ── File paths ─────────────────────────────────────────────────────────────────
ROOT_DIR       = Path(__file__).parent.parent
DATA_DIR       = ROOT_DIR / "data"
RAW_DIR        = DATA_DIR / "raw"
PROCESSED_DIR  = DATA_DIR / "processed"
CLASSIFIED_DIR = DATA_DIR / "classified"
TILES_DIR      = DATA_DIR / "tiles"
TRAINING_DIR   = DATA_DIR / "training"
MODELS_DIR     = ROOT_DIR / "models"
