from __future__ import annotations

import aiofiles
from fastapi import APIRouter, Request

from ..config import settings
from ..models import UploadResponse
from ..services import pipeline
from ..utils import create_job_id, job_file_name

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_glb(request: Request) -> UploadResponse:
    """스트리밍 업로드 — 100MB+ 파일을 메모리 버퍼링 없이 디스크에 직접 저장."""
    filename = request.query_params.get("filename", "input.glb")

    settings.staging_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    job_id = create_job_id(filename)
    fname = job_file_name(job_id, filename)

    async with aiofiles.open(settings.staging_dir / fname, "wb") as f:
        async for chunk in request.stream():
            await f.write(chunk)

    pipeline.create_job(job_id, filename)

    return UploadResponse(
        job_id=job_id,
        input_url=f"/files/staging/{fname}",
    )
