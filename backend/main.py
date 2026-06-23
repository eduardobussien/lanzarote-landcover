"""
FastAPI application entry point.

Run locally:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

Endpoints:
    GET  /health                  - liveness probe
    GET  /api/v1/metadata         - project metadata (always available)
    GET  /api/v1/time-series      - area per class per year (needs notebook 04 CSVs)
    GET  /api/v1/transitions      - transition matrix 1990-2023 (needs notebook 04 CSVs)
    GET  /api/v1/tiles/{year}     - GEE tile URL for classified map (needs EE credentials)
    GET  /                        - frontend UI (served from frontend/index.html)

Docs:
    http://localhost:8000/docs    (Swagger UI)
    http://localhost:8000/redoc   (ReDoc)
"""

import pathlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routers.analysis import router as analysis_router
from backend.routers.tiles import router as tiles_router

ROOT_DIR = pathlib.Path(__file__).parent.parent

app = FastAPI(
    title="Lanzarote Land Cover API",
    description="Historical land cover change analysis for Lanzarote, Canary Islands.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis_router)
app.include_router(tiles_router)


@app.get("/health", tags=["meta"])
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


# Serve the frontend at / - must be mounted after all routes
_frontend = ROOT_DIR / "frontend"
if _frontend.exists():
    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")
