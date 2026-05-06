from __future__ import annotations

import re
import uuid


def sanitize_filename(name: str) -> str:
    """파일시스템에 위험한 문자만 제거하고 원본 이름을 최대한 보존."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    return name.strip('. ') or "file"


def _safe_stem(original_filename: str) -> str:
    safe = sanitize_filename(original_filename)
    if "." in safe:
        stem, _ = safe.rsplit(".", 1)
        return stem or "file"
    return safe


def create_job_id(original_filename: str) -> str:
    """e.g. 'test02_a1b2c3d4'"""
    return f"{_safe_stem(original_filename)}_{uuid.uuid4().hex[:8]}"


def output_file_name(job_id: str, original_filename: str) -> str:
    """e.g. 'test02_a1b2c3d4.glb'"""
    safe = sanitize_filename(original_filename)
    if "." in safe:
        _, ext = safe.rsplit(".", 1)
        return f"{job_id}.{ext}"
    return job_id


def job_file_name(job_id: str, original_filename: str) -> str:
    """Backward-compatible alias for output file names."""
    return output_file_name(job_id, original_filename)
