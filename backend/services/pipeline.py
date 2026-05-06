from __future__ import annotations

import asyncio
import sys
import tempfile
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from ..config import settings
from ..models import JobStatus, PipelineParams, PipelineStep
from ..utils import output_file_name

_jobs: dict[str, JobStatus] = {}
_queue: asyncio.Queue[str] = asyncio.Queue()
_pending_params: dict[str, PipelineParams] = {}
_worker_task: asyncio.Task | None = None

# stdout 패턴 → step index 매핑
_STEP_MARKERS = {
    "extract_for_qem.py": 0,
    "qem_simplify.py": 1,
    "bake_export.py": 2,
}
_STEP_NAMES = ["extract", "simplify", "bake"]


def get_job(job_id: str) -> Optional[JobStatus]:
    return _jobs.get(job_id)


def list_jobs() -> list[JobStatus]:
    return list(_jobs.values())


def create_job(job_id: str, input_filename: str) -> JobStatus:
    job = JobStatus(
        job_id=job_id,
        status="uploading",
        steps=[
            PipelineStep(name="extract", status="pending"),
            PipelineStep(name="simplify", status="pending"),
            PipelineStep(name="bake", status="pending"),
        ],
        input_filename=input_filename,
    )
    _jobs[job_id] = job
    return job


def enqueue_job(job_id: str, params: PipelineParams) -> None:
    job = _jobs[job_id]
    job.status = "queued"
    _pending_params[job_id] = params
    _queue.put_nowait(job_id)


async def start_worker() -> None:
    global _worker_task
    _worker_task = asyncio.create_task(_worker_loop())


async def _worker_loop() -> None:
    while True:
        job_id = await _queue.get()
        params = _pending_params.pop(job_id, PipelineParams())
        try:
            await run_pipeline_async(job_id, params)
        except Exception:
            pass
        finally:
            _queue.task_done()


async def run_pipeline_async(job_id: str, params: PipelineParams) -> None:
    job = _jobs.get(job_id)
    if not job:
        return

    output_fname = output_file_name(job_id, job.input_filename)
    input_glb = settings.staging_dir / output_fname
    output_glb = settings.output_dir / output_fname

    settings.output_dir.mkdir(parents=True, exist_ok=True)

    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    job.steps[0].status = "running"
    job.step = "extract"

    log_buffer: deque[str] = deque(maxlen=10)
    current_step_idx = 0

    try:
        with tempfile.TemporaryDirectory(prefix="glb_opt_") as workdir:
            cmd = [
                sys.executable,
                str(settings.pipeline_root / "run_pipeline.py"),
                "--input", str(input_glb),
                "--output", str(output_glb),
                "--blender", settings.blender_path,
                "--workdir", workdir,
                "--tris-ratio", str(params.tris_ratio),
                "--texture-ratio", str(params.texture_ratio),
            ]
            if params.target_tris:
                cmd += ["--target-tris", str(params.target_tris)]
            if params.texture_size:
                cmd += ["--texture-size", str(params.texture_size)]
            if params.skip_high_poly_cleanup:
                cmd.append("--skip-high-poly-cleanup")
            if params.skip_cage:
                cmd.append("--skip-cage")

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(settings.pipeline_root),
            )

            async for line_bytes in proc.stdout:  # type: ignore[union-attr]
                line = line_bytes.decode("utf-8", errors="replace").rstrip()
                log_buffer.append(line)

                for marker, step_idx in _STEP_MARKERS.items():
                    if marker in line and step_idx > current_step_idx:
                        job.steps[current_step_idx].status = "done"
                        current_step_idx = step_idx
                        job.steps[current_step_idx].status = "running"
                        job.step = _STEP_NAMES[current_step_idx]
                        break

                job.steps[current_step_idx].log_tail = "\n".join(log_buffer)

            await proc.wait()

        if proc.returncode == 0:
            for step in job.steps:
                step.status = "done"
            job.status = "done"
            job.step = None
            job.output_url = f"/files/output/{output_fname}"
        else:
            job.steps[current_step_idx].status = "error"
            job.status = "error"
            job.error = "\n".join(log_buffer)

    except Exception as exc:
        job.status = "error"
        job.error = str(exc)
    finally:
        job.finished_at = datetime.now(timezone.utc)
