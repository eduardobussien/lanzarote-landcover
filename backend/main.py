"""
FastAPI application entry point.

Run locally:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

API docs available at:
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc  (ReDoc)

Status: Phase 4 - not yet implemented.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.analysis import router as analysis_router

app = FastAPI(
    title="Lanzarote Land Cover API",
    description="Historical land cover change analysis for the Canary Islands.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],   # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


app.include_router(analysis_router)
