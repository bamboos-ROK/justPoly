from __future__ import annotations

import aiofiles
import aiofiles.os
from fastapi import APIRouter, HTTPException, Request

from ..config import settings
from ..models import UploadResponse
from ..services import pipeline
from ..utils import create_job_id, job_file_name

router = APIRouter()

MAX_FILE_SIZE = 300 * 1024 * 1024  # 300MB


@router.post("/upload", response_model=UploadResponse)
async def upload_glb(request: Request) -> UploadResponse:
    """스트리밍 업로드 — 100MB+ 파일을 메모리 버퍼링 없이 디스크에 직접 저장."""
    filename = request.query_params.get("filename", "input.glb")

    if not filename.lower().endswith(".glb"):
        raise HTTPException(400, "Only .glb files are accepted")

    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_FILE_SIZE:
        raise HTTPException(413, "File exceeds 300MB limit")

    settings.staging_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    job_id = create_job_id(filename)
    fname = job_file_name(job_id, filename)
    staging_path = settings.staging_dir / fname

    total_bytes = 0
    async with aiofiles.open(staging_path, "wb") as f:
        async for chunk in request.stream():
            total_bytes += len(chunk)
            if total_bytes > MAX_FILE_SIZE:
                await f.aclose()
                await aiofiles.os.remove(staging_path)
                raise HTTPException(413, "File exceeds 300MB limit")
            await f.write(chunk)

    if total_bytes == 0:
        await aiofiles.os.remove(staging_path)
        raise HTTPException(400, "Empty file rejected")

    job = pipeline.create_job(job_id, filename)
    job.status = "uploaded"

    return UploadResponse(
        job_id=job_id,
        input_url=f"/files/staging/{fname}",
    )
