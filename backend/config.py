import pathlib

ROOT_DIR = pathlib.Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data" / "processed"

AREA_CSV       = DATA_DIR / "area_time_series.csv"
TRANSITION_CSV = DATA_DIR / "transition_matrix_1990_2023.csv"

PROJECT_METADATA = {
    "project":     "Lanzarote Land Cover Change Analysis",
    "study_area":  "Lanzarote, Canary Islands, Spain",
    "bbox":        {"west": -13.92, "south": 28.80, "east": -13.30, "north": 29.30},
    "years":       [1990, 1995, 2000, 2002, 2010, 2015, 2020, 2023],
    "classes":     ["Urban/Built-up", "Water/Wetland", "Agriculture", "Barren/Volcanic"],
    "classifier":  {"name": "Random Forest", "n_trees": 200, "oa": 0.667, "kappa": 0.52},
    "imagery":     "Landsat Collection 2 Level-2 Surface Reflectance (USGS/NASA)",
    "labels":      "CORINE Land Cover 2018 (Copernicus/EEA)",
}
