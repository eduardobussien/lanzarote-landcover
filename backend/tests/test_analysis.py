"""Basic smoke tests for the analysis endpoints."""
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_metadata_shape():
    r = client.get("/api/v1/metadata")
    assert r.status_code == 200
    body = r.json()
    assert "project" in body
    assert "classes" in body
    assert "classifier" in body
    assert len(body["classes"]) == 4


def test_time_series_or_503():
    r = client.get("/api/v1/time-series")
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        body = r.json()
        assert "years" in body
        assert "data" in body
        assert len(body["data"]) > 0


def test_transitions_or_503():
    r = client.get("/api/v1/transitions")
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        body = r.json()
        assert "matrix_km2" in body
        assert "changed_pct" in body
        assert 0 <= body["changed_pct"] <= 100
