from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(str, Enum):
    QUEUED = "queued"
    AWAITING_APPROVAL = "awaiting_approval"
    RENDERING = "rendering"
    DONE = "done"
    FAILED = "failed"


class JobStage(str, Enum):
    ASSET_UPLOAD = "asset_upload"
    CLIP_1_GEN = "clip_1_gen"
    CLIP_1_REVIEW = "clip_1_review"
    CLIP_2_GEN = "clip_2_gen"
    CLIP_3_GEN = "clip_3_gen"
    ASSEMBLY = "assembly"
    DONE = "done"


@dataclass
class Job:
    client_slug: str
    format_seconds: int
    created_by: str | None = None
    idempotency_key: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.QUEUED
    stage: JobStage = JobStage.ASSET_UPLOAD
    clip_total: int = 2
    clip_1_approved: bool = False
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)


@dataclass
class RunEvent:
    job_id: str
    event_type: str
    payload: dict[str, Any]
    trace_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=now_utc)
