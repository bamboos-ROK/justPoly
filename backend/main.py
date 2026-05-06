from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import upload, jobs, files
from .services import pipeline as pipeline_service

app = FastAPI(title="GLB Optimizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    settings.staging_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/files/staging", StaticFiles(directory=str(settings.staging_dir)), name="staging")
    app.mount("/files/output", StaticFiles(directory=str(settings.output_dir)), name="output")
    await pipeline_service.start_worker()


app.include_router(upload.router)
app.include_router(jobs.router)
app.include_router(files.router)
