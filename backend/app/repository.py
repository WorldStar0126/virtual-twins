from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from backend.app.models import Job, JobStage, JobStatus, RunEvent


class Repository(Protocol):
    def create_job(self, job: Job) -> Job: ...
    def get_job(self, job_id: str) -> Job | None: ...
    def get_job_by_idempotency(self, idempotency_key: str) -> Job | None: ...
    def save_job(self, job: Job) -> Job: ...
    def append_event(self, job_id: str, event_type: str, payload: dict[str, Any]) -> RunEvent: ...
    def list_events(self, job_id: str) -> list[RunEvent]: ...


class InMemoryRepository:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.events_by_job: dict[str, list[RunEvent]] = defaultdict(list)
        self.jobs_by_idempotency: dict[str, str] = {}

    def create_job(self, job: Job) -> Job:
        if job.idempotency_key:
            key = job.idempotency_key
            existing_id = self.jobs_by_idempotency.get(key)
            if existing_id:
                return self.jobs[existing_id]
            self.jobs_by_idempotency[key] = job.id

        self.jobs[job.id] = job
        self.append_event(
            job.id,
            "job_created",
            {
                "status": job.status.value,
                "stage": job.stage.value,
                "format_seconds": job.format_seconds,
                "clip_total": job.clip_total,
            },
        )
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def get_job_by_idempotency(self, idempotency_key: str) -> Job | None:
        job_id = self.jobs_by_idempotency.get(idempotency_key)
        if not job_id:
            return None
        return self.jobs.get(job_id)

    def save_job(self, job: Job) -> Job:
        job.updated_at = datetime.now(timezone.utc)
        self.jobs[job.id] = job
        return job

    def append_event(self, job_id: str, event_type: str, payload: dict[str, Any]) -> RunEvent:
        event = RunEvent(
            job_id=job_id,
            event_type=event_type,
            payload=payload,
            trace_id=str(uuid4()),
        )
        self.events_by_job[job_id].append(event)
        return event

    def list_events(self, job_id: str) -> list[RunEvent]:
        return self.events_by_job.get(job_id, [])


class PostgresRepository:
    def create_job(self, job: Job) -> Job:
        from sqlalchemy import select

        from backend.app.db import SessionLocal
        from backend.app.db_models import JobTable

        with SessionLocal() as session:
            if job.idempotency_key:
                existing = session.execute(
                    select(JobTable).where(
                        JobTable.idempotency_key == job.idempotency_key,
                    )
                ).scalar_one_or_none()
                if existing:
                    return self._row_to_job(existing)

            row = JobTable(
                id=job.id,
                scope_id="default_scope",
                client_slug=job.client_slug,
                format_seconds=job.format_seconds,
                status=job.status.value,
                stage=job.stage.value,
                clip_total=job.clip_total,
                clip_1_approved=job.clip_1_approved,
                created_by=job.created_by,
                idempotency_key=job.idempotency_key,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
            session.add(row)
            session.commit()
            self.append_event(
                job.id,
                "job_created",
                {
                    "status": job.status.value,
                    "stage": job.stage.value,
                    "format_seconds": job.format_seconds,
                    "clip_total": job.clip_total,
                },
            )
            return job

    def get_job(self, job_id: str) -> Job | None:
        from backend.app.db import SessionLocal
        from backend.app.db_models import JobTable

        with SessionLocal() as session:
            row = session.get(JobTable, job_id)
            if not row:
                return None
            return self._row_to_job(row)

    def get_job_by_idempotency(self, idempotency_key: str) -> Job | None:
        from sqlalchemy import select

        from backend.app.db import SessionLocal
        from backend.app.db_models import JobTable

        with SessionLocal() as session:
            row = session.execute(
                select(JobTable).where(
                    JobTable.idempotency_key == idempotency_key,
                )
            ).scalar_one_or_none()
            if not row:
                return None
            return self._row_to_job(row)

    def save_job(self, job: Job) -> Job:
        from backend.app.db import SessionLocal
        from backend.app.db_models import JobTable

        with SessionLocal() as session:
            row = session.get(JobTable, job.id)
            if not row:
                return job
            row.status = job.status.value
            row.stage = job.stage.value
            row.clip_total = job.clip_total
            row.clip_1_approved = job.clip_1_approved
            row.updated_at = datetime.now(timezone.utc)
            session.commit()
            return self._row_to_job(row)

    def append_event(self, job_id: str, event_type: str, payload: dict[str, Any]) -> RunEvent:
        from backend.app.db import SessionLocal
        from backend.app.db_models import RunEventTable

        event = RunEvent(
            job_id=job_id,
            event_type=event_type,
            payload=payload,
            trace_id=str(uuid4()),
        )
        with SessionLocal() as session:
            row = RunEventTable(
                id=event.id,
                job_id=event.job_id,
                event_type=event.event_type,
                trace_id=event.trace_id,
                payload=event.payload,
                created_at=event.created_at,
            )
            session.add(row)
            session.commit()
        return event

    def list_events(self, job_id: str) -> list[RunEvent]:
        from sqlalchemy import select

        from backend.app.db import SessionLocal
        from backend.app.db_models import RunEventTable

        with SessionLocal() as session:
            rows = session.execute(
                select(RunEventTable).where(RunEventTable.job_id == job_id).order_by(RunEventTable.created_at.asc())
            ).scalars()
            return [
                RunEvent(
                    id=row.id,
                    job_id=row.job_id,
                    event_type=row.event_type,
                    trace_id=row.trace_id,
                    payload=row.payload,
                    created_at=row.created_at,
                )
                for row in rows
            ]

    @staticmethod
    def _row_to_job(row: Any) -> Job:
        return Job(
            id=row.id,
            client_slug=row.client_slug,
            format_seconds=row.format_seconds,
            status=JobStatus(row.status),
            stage=JobStage(row.stage),
            clip_total=row.clip_total,
            clip_1_approved=row.clip_1_approved,
            created_by=row.created_by,
            idempotency_key=row.idempotency_key,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


def build_repository() -> Repository:
    backend = os.getenv("VT_STORAGE_BACKEND", "memory").strip().lower()
    if backend == "postgres":
        return PostgresRepository()
    return InMemoryRepository()
