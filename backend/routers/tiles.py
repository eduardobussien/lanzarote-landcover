"""Tile URL endpoint - returns GEE XYZ tile URL for a classified year map."""
from fastapi import APIRouter, HTTPException

from backend.services.gee_service import get_tile_url

router = APIRouter(prefix="/api/v1", tags=["tiles"])

VALID_YEARS = {1990, 1995, 2000, 2002, 2010, 2015, 2020, 2023}


@router.get("/tiles/{year}")
def get_tile_url_for_year(year: int):
    """Return the XYZ tile URL for the GEE classified land cover map for *year*.

    First call per year takes 30-60 s (GEE training + classification).
    Subsequent calls for the same year are instant (cached).
    """
    if year not in VALID_YEARS:
        raise HTTPException(
            status_code=400,
            detail=f"year must be one of {sorted(VALID_YEARS)}",
        )
    try:
        url = get_tile_url(year)
        return {"year": year, "tile_url": url}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"GEE error: {e}") from e
