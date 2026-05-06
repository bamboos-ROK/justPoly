from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class PipelineParams(BaseModel):
    tris_ratio: float = 0.1
    texture_ratio: float = 0.5
    target_tris: Optional[int] = None
    texture_size: Optional[int] = None
    skip_high_poly_cleanup: bool = False
    skip_cage: bool = False


class StartPipelineRequest(BaseModel):
    job_id: str
    params: PipelineParams = PipelineParams()


class PipelineStep(BaseModel):
    name: str
    status: Literal["pending", "running", "done", "error"]
    log_tail: str = ""


class JobStatus(BaseModel):
    job_id: str
    status: Literal["uploading", "running", "done", "error"]
    step: Optional[str] = None
    steps: list[PipelineStep]
    input_filename: str
    output_url: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class UploadResponse(BaseModel):
    job_id: str
    input_url: str


class OutputFile(BaseModel):
    job_id: str
    filename: str
    input_url: str
    output_url: str
    size_bytes: int
    created_at: datetime
