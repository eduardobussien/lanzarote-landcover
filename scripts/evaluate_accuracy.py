"""Hold-out accuracy of the classifier the app serves (Landsat 8 era, 2014-2023).

Mirrors backend/services/gee_service.py: an L8+L9 dry-season composite over the
2016-2020 training window, CORINE 2018 labels and 750 stratified points per
class. The difference is that 30% of the points are held back, never used for
training, and used only to score:

  (a) the raw Random Forest, and
  (b) the final majority-filtered map that the app actually displays.

Accuracy here means AGREEMENT WITH CORINE 2018, not ground truth. CORINE maps
blocks of at least 25 ha, so some disagreement is CORINE generalising (e.g.
gardens and roads inside an "urban" polygon), not the model being wrong. The
split is random rather than spatial, so neighbouring train/test points make the
score somewhat optimistic.

The app's served classifier is trained on ALL points, so the hold-out score is a
slightly conservative estimate for it.

Run from the repo root (needs Earth Engine credentials):
    python scripts/evaluate_accuracy.py                # print the report
    python scripts/evaluate_accuracy.py result.json    # also save raw numbers
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ee  # noqa: E402

from backend.services import gee_service as g  # noqa: E402

TEST_FRACTION = 0.3
SPLIT_SEED = 7
CLASS_NAMES = ["Urban", "Water", "Agriculture", "Barren"]   # order of g.ACTIVE_CLASSES


def main(out_path: str | None = None) -> None:
    g._init_base()
    cfg = g.SENSOR_CONFIG["L8"]
    aoi = g._aoi

    labels = (
        ee.Image(cfg["corine"]).select("landcover").clip(aoi)
        .remap(list(g.CORINE_REMAP.keys()), list(g.CORINE_REMAP.values()), defaultValue=-1)
        .rename("label")
    )
    labels = labels.updateMask(labels.gte(0))

    comp = g._composite("L8", cfg["train_start"], cfg["train_end"])
    samples = comp.select(g.FEATURE_BANDS).addBands(labels).stratifiedSample(
        numPoints=750, classBand="label", region=aoi, scale=100,
        classValues=g.ACTIVE_CLASSES, classPoints=[750] * len(g.ACTIVE_CLASSES),
        seed=42, geometries=True,
    ).randomColumn("rand", seed=SPLIT_SEED)

    train = samples.filter(ee.Filter.lt("rand", 1 - TEST_FRACTION))
    test = samples.filter(ee.Filter.gte("rand", 1 - TEST_FRACTION))

    clf = ee.Classifier.smileRandomForest(numberOfTrees=200, seed=42).train(
        features=train, classProperty="label", inputProperties=g.FEATURE_BANDS,
    )
    order = g.ACTIVE_CLASSES

    # (a) raw classifier on the held-out points
    raw_em = test.classify(clf).errorMatrix("label", "classification", order)

    # (b) the filtered map the app shows, sampled at the same held-out points
    raw_img = (
        comp.select(g.FEATURE_BANDS).classify(clf).rename("classification").toInt()
        .updateMask(g._land_mask)
    )
    smoothed = raw_img.focalMode(
        radius=g.MAJORITY_FILTER_RADIUS, kernelType="square", units="pixels",
    )
    final = smoothed.where(raw_img.eq(0), 0).updateMask(raw_img.mask())
    map_em = final.sampleRegions(
        collection=test, properties=["label"], scale=30,
        projection=ee.Projection(f"EPSG:{g.CRS_EPSG_INT}"),
    ).errorMatrix("label", "classification", order)

    def summarize(em):
        return {
            "overall": em.accuracy(),
            "kappa": em.kappa(),
            "recall": em.producersAccuracy().project([0]),
            "precision": em.consumersAccuracy().project([1]),
            "matrix": em.array(),
        }

    result = ee.Dictionary({
        "n_train": train.size(),
        "n_test": test.size(),
        "raw": summarize(raw_em),
        "map": summarize(map_em),
    }).getInfo()

    print(f"train points: {result['n_train']}, held-out test points: {result['n_test']}")
    for key, title in (("raw", "RAW classifier"), ("map", "FILTERED map (what the app shows)")):
        r = result[key]
        print(f"\n== {title} ==")
        print(f"overall accuracy {r['overall']:.3f}   kappa {r['kappa']:.3f}")
        print(f"{'class':<12}{'recall':>8}{'precision':>11}   (rows = CORINE truth, cols = predicted)")
        for i, name in enumerate(CLASS_NAMES):
            print(f"{name:<12}{r['recall'][i]:>8.2f}{r['precision'][i]:>11.2f}   {r['matrix'][i]}")

    if out_path:
        Path(out_path).write_text(json.dumps(result, indent=2))
        print(f"\nsaved {out_path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
