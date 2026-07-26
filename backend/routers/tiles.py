"""Live GEE endpoints - classified tile URLs and per-class areas for a year."""
import traceback

from fastapi import APIRouter, HTTPException

from backend.services.gee_service import (
    get_change_map,
    get_class_areas,
    get_tile_url,
)

router = APIRouter(prefix="/api/v1", tags=["tiles"])

MIN_YEAR = 1985
MAX_YEAR = 2024


def _check_year(year: int) -> None:
    if not (MIN_YEAR <= year <= MAX_YEAR):
        raise HTTPException(
            status_code=400,
            detail=f"year must be between {MIN_YEAR} and {MAX_YEAR}",
        )


@router.get("/tiles/{year}")
def get_tile_url_for_year(year: int):
    """Return the XYZ tile URL for the GEE classified land cover map for *year*.

    First call per sensor era takes 30-60 s (GEE training + classification).
    Subsequent calls for the same year are instant (cached).
    """
    _check_year(year)
    try:
        return {"year": year, "tile_url": get_tile_url(year)}
    except Exception as e:
        print(f"\n=== GEE tile error for year {year} ===")
        traceback.print_exc()
        print("=======================================\n")
        raise HTTPException(status_code=503, detail=f"GEE error: {e}") from e


@router.get("/areas/{year}")
def get_areas_for_year(year: int):
    """Return per-class area (km2) for *year*, computed from the same live
    classification that draws the map - so numbers always match the map.
    """
    _check_year(year)
    try:
        return {"year": year, "areas": get_class_areas(year)}
    except Exception as e:
        print(f"\n=== GEE area error for year {year} ===")
        traceback.print_exc()
        print("=======================================\n")
        raise HTTPException(status_code=503, detail=f"GEE error: {e}") from e


@router.get("/change/{year_a}/{year_b}")
def get_change_for_years(year_a: int, year_b: int):
    """Return a change-map tile URL + how much land changed class between two years."""
    _check_year(year_a)
    _check_year(year_b)
    if year_a == year_b:
        raise HTTPException(status_code=400, detail="Pick two different years to compare")
    try:
        return {"from": year_a, "to": year_b, **get_change_map(year_a, year_b)}
    except Exception as e:
        print(f"\n=== GEE change error for {year_a}->{year_b} ===")
        traceback.print_exc()
        print("=======================================\n")
        raise HTTPException(status_code=503, detail=f"GEE error: {e}") from e
