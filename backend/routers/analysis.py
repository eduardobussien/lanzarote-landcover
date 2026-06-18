import pandas as pd
from fastapi import APIRouter, HTTPException

from backend.config import AREA_CSV, PROJECT_METADATA, TRANSITION_CSV
from backend.schemas.analysis import (
    ClassAreaPoint,
    MetadataResponse,
    TimeSeriesResponse,
    TransitionResponse,
)

router = APIRouter(prefix="/api/v1", tags=["analysis"])


def _load_area() -> pd.DataFrame:
    if not AREA_CSV.exists():
        raise HTTPException(
            status_code=503,
            detail="Area data not found. Run notebook 04 to generate it.",
        )
    return pd.read_csv(AREA_CSV)


def _load_transition() -> pd.DataFrame:
    if not TRANSITION_CSV.exists():
        raise HTTPException(
            status_code=503,
            detail="Transition data not found. Run notebook 04 to generate it.",
        )
    return pd.read_csv(TRANSITION_CSV, index_col=0)


@router.get("/time-series", response_model=TimeSeriesResponse)
def get_time_series():
    """Area (km2) per land cover class for each target year."""
    df = _load_area()
    points = [
        ClassAreaPoint(
            year=int(row["year"]),
            class_name=row["class_name"],
            area_km2=round(float(row["area_km2"]), 2),
        )
        for _, row in df.iterrows()
    ]
    return TimeSeriesResponse(
        years=sorted(df["year"].unique().tolist()),
        classes=df["class_name"].unique().tolist(),
        data=points,
    )


@router.get("/transitions", response_model=TransitionResponse)
def get_transitions():
    """Land cover transition matrix (km2) between 1990 and 2023."""
    df = _load_transition()
    classes = df.index.tolist()
    matrix  = df.values.round(2).tolist()

    stable_km2  = float(sum(df.loc[c, c] for c in classes))
    total_km2   = float(df.values.sum())
    changed_km2 = total_km2 - stable_km2

    return TransitionResponse(
        from_year   = 1990,
        to_year     = 2023,
        classes     = classes,
        matrix_km2  = matrix,
        stable_km2  = round(stable_km2, 1),
        changed_km2 = round(changed_km2, 1),
        changed_pct = round(changed_km2 / total_km2 * 100, 1) if total_km2 else 0.0,
    )


@router.get("/metadata", response_model=MetadataResponse)
def get_metadata():
    """Project metadata: study area, classifier, imagery source."""
    return MetadataResponse(**PROJECT_METADATA)
