from pydantic import BaseModel


class ClassAreaPoint(BaseModel):
    year: int
    class_name: str
    area_km2: float


class TimeSeriesResponse(BaseModel):
    years: list[int]
    classes: list[str]
    data: list[ClassAreaPoint]


class TransitionResponse(BaseModel):
    from_year: int
    to_year: int
    classes: list[str]
    matrix_km2: list[list[float]]
    stable_km2: float
    changed_km2: float
    changed_pct: float


class MetadataResponse(BaseModel):
    project: str
    study_area: str
    bbox: dict
    years: list[int]
    classes: list[str]
    classifier: dict
    imagery: str
    labels: str
