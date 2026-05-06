from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..models import OutputFile, PipelineParams
from ..services import pipeline

router = APIRouter()


def _input_filename_from_output(output_path: Path, job_id: str) -> str:
    parts = job_id.rsplit("_", 1)
    if len(parts) == 2:
        return f"{parts[0]}{output_path.suffix}"
    return output_path.name


def _read_output_metadata(output_path: Path) -> dict[str, Any]:
    metadata_path = output_path.with_suffix(".json")
    if not metadata_path.exists():
        return {}
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


@router.get("/outputs", response_model=list[OutputFile])
async def list_outputs() -> list[OutputFile]:
    results: list[OutputFile] = []

    if not settings.output_dir.exists():
        return results

    for f in settings.output_dir.iterdir():
        if not f.is_file() or f.suffix.lower() != ".glb":
            continue

        job_id = f.stem
        job = pipeline.get_job(job_id)
        metadata = _read_output_metadata(f)
        filename = (
            job.input_filename
            if job
            else metadata.get("filename") or _input_filename_from_output(f, job_id)
        )
        input_path = settings.staging_dir / f.name
        params = job.params if job else None
        if params is None and isinstance(metadata.get("params"), dict):
            try:
                params = PipelineParams.model_validate(metadata["params"])
            except ValueError:
                params = None

        results.append(
            OutputFile(
                job_id=job_id,
                filename=filename,
                input_url=f"/files/staging/{f.name}" if input_path.exists() else "",
                output_url=f"/files/output/{f.name}",
                size_bytes=f.stat().st_size,
                created_at=datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc),
                params=params,
            )
        )

    return sorted(results, key=lambda x: x.created_at, reverse=True)


@router.delete("/outputs/{job_id}", status_code=204)
async def delete_output(job_id: str) -> None:
    output_glb = settings.output_dir / f"{job_id}.glb"
    if not output_glb.exists():
        raise HTTPException(404, "Output not found")
    output_glb.unlink()
    meta = output_glb.with_suffix(".json")
    if meta.exists():
        meta.unlink()
    staging_glb = settings.staging_dir / f"{job_id}.glb"
    if staging_glb.exists():
        staging_glb.unlink()
    pipeline.delete_job(job_id)
