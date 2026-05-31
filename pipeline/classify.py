"""
Land Cover Classification
==========================

Random Forest classifier trained on CORINE Land Cover labels.

Workflow
--------
1. Load CORINE raster for the AOI (ground truth labels)
2. Remap CORINE 44 classes → 6 simplified classes (see config.CORINE_REMAP)
3. Build feature stack per pixel:
   [blue, green, red, nir, swir1, swir2, ndvi, ndwi, ndbi, savi, bsi, evi, mndwi]
   + optional: elevation, slope (from SRTM DEM)
4. Stratified train/validation split (70/30, spatially blocked)
5. Train Random Forest with class_weight='balanced'
6. Evaluate: confusion matrix, per-class F1, Overall Accuracy, Kappa
7. Apply to all annual composites → classified GeoTIFFs

Notes
-----
- CORINE resolution is 100m; Landsat is 30m. When sampling training pixels,
  only use pixels well inside CORINE class polygons (buffer inward ~50m)
  to avoid mixed-class boundary effects.
- Use spatial block cross-validation, NOT random pixel splits —
  random splits inflate accuracy due to spatial autocorrelation.
"""

# TODO (Phase 2): Implement classifier training and prediction

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, cohen_kappa_score
import numpy as np

from pipeline.config import CLASS_NAMES, N_CLASSES


def build_feature_stack(bands: dict, indices: dict,
                        elevation: np.ndarray | None = None) -> np.ndarray:
    """
    Flatten spatial arrays into a (n_pixels, n_features) matrix.
    Feature order matches the trained model — do not reorder.
    """
    raise NotImplementedError("Phase 2")


def sample_training_pixels(feature_stack: np.ndarray,
                           label_map: np.ndarray,
                           n_per_class: int = 5000) -> tuple:
    """
    Stratified sampling of training pixels.
    Returns (X_train, X_val, y_train, y_val).
    """
    raise NotImplementedError("Phase 2")


def train_classifier(X_train: np.ndarray, y_train: np.ndarray) -> RandomForestClassifier:
    """
    Train a Random Forest with settings tuned for spectral classification.
    """
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        min_samples_split=10,
        min_samples_leaf=5,
        class_weight="balanced",   # handles class imbalance (urban << volcanic)
        n_jobs=-1,
        random_state=42,
    )
    raise NotImplementedError("Phase 2 — fit clf and return it")


def evaluate_classifier(clf, X_val: np.ndarray, y_val: np.ndarray) -> dict:
    """
    Compute accuracy metrics.
    Returns dict with keys: overall_accuracy, kappa, confusion_matrix, report.

    Target benchmarks:
      Overall Accuracy > 85%  (good)  / > 90%  (excellent)
      Kappa            > 0.80 (good)  / > 0.85 (excellent)
    """
    raise NotImplementedError("Phase 2")


def classify_image(clf, feature_stack: np.ndarray,
                   height: int, width: int) -> np.ndarray:
    """
    Apply a trained classifier to a full image.
    Returns classified map of shape (height, width).
    """
    raise NotImplementedError("Phase 2")
