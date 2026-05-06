from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import upload, jobs, files
from .services import pipeline as pipeline_service

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
frontend_index = frontend_dist / "index.html"

app = FastAPI(title="JustPoly API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.staging_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)
app.mount("/files/staging", StaticFiles(directory=str(settings.staging_dir)), name="staging")
app.mount("/files/output", StaticFiles(directory=str(settings.output_dir)), name="output")


def _is_spa_navigation(request: Request) -> bool:
    if request.method != "GET" or not frontend_index.exists():
        return False

    path = request.url.path
    if path.startswith("/api/") or path.startswith("/assets/") or path.startswith("/files/"):
        return False

    accept = request.headers.get("accept", "")
    return "text/html" in accept


@app.middleware("http")
async def serve_spa_navigation(request: Request, call_next):
    if _is_spa_navigation(request):
        return FileResponse(frontend_index)
    return await call_next(request)


@app.on_event("startup")
async def startup() -> None:
    await pipeline_service.start_worker()


app.include_router(upload.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(files.router, prefix="/api")

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist)), name="frontend")
