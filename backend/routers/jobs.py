from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..models import JobStatus, StartPipelineRequest
from ..services import pipeline

router = APIRouter()


@router.post("/jobs", response_model=JobStatus)
async def start_pipeline(body: StartPipelineRequest, bg: BackgroundTasks) -> JobStatus:
    job = pipeline.get_job(body.job_id)
    if not job:
        raise HTTPException(404, "job_id not found. Upload first.")
    if job.status != "uploading":
        raise HTTPException(409, f"Job already in status: {job.status}")

    bg.add_task(pipeline.run_pipeline_async, body.job_id, body.params)
    return job


@router.get("/jobs", response_model=list[JobStatus])
async def list_jobs() -> list[JobStatus]:
    return pipeline.list_jobs()


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str) -> JobStatus:
    job = pipeline.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job
