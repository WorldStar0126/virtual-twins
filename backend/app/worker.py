from __future__ import annotations

import os
from uuid import uuid4

from typing import Protocol

from backend.app.models import Job, JobStage, JobStatus
from backend.app.observability import telemetry
from backend.app.queue import QueueMessage, TaskQueue, make_queue_message
from backend.app.state_machine import advance_to_clip_1_review


class WorkerStore(Protocol):
    def get_job(self, job_id: str) -> Job | None: ...
    def save_job(self, job: Job) -> Job: ...
    def append_event(self, job_id: str, event_type: str, payload: dict) -> object: ...


class WorkerService:
    """
    Phase 1 worker skeleton.

    Queue-backed worker orchestration.
    """

    def __init__(self, data_store: WorkerStore, task_queue: TaskQueue) -> None:
        self.store = data_store
        self.queue = task_queue

    def enqueue_clip_1_generation(self, job: Job) -> Job:
        max_attempts = int(os.getenv("VT_RETRY_MAX_ATTEMPTS", "3"))
        job.status = JobStatus.QUEUED
        job.stage = JobStage.ASSET_UPLOAD
        self.store.save_job(job)
        trace_id = str(uuid4())
        self.store.append_event(
            job.id,
            "clip_1_generation_queued",
            {"status": job.status.value, "stage": job.stage.value, "trace_id": trace_id},
        )
        telemetry.incr("worker.tasks.enqueued")
        self.queue.enqueue(
            make_queue_message(
                job_id=job.id,
                task_type="generate_clip_1",
                task_key=f"{job.id}:clip_1_generation",
                trace_id=trace_id,
                attempt=1,
                max_attempts=max_attempts,
            )
        )
        return job

    def process_clip_1_generation(self, message: QueueMessage) -> Job | None:
        job = self.store.get_job(message.job_id)
        if not job:
            return None
        if job.stage == JobStage.CLIP_1_REVIEW:
            telemetry.incr("worker.tasks.duplicate_ignored")
            self.store.append_event(
                job.id,
                "duplicate_task_ignored",
                {
                    "task_key": message.task_key,
                    "attempt": message.attempt,
                    "trace_id": message.trace_id,
                    "reason": "job already at approval gate",
                },
            )
            return job

        job.status = JobStatus.RENDERING
        job.stage = JobStage.CLIP_1_GEN
        self.store.save_job(job)
        self.store.append_event(
            job.id,
            "clip_1_generation_started",
            {
                "status": job.status.value,
                "stage": job.stage.value,
                "attempt": message.attempt,
                "trace_id": message.trace_id,
            },
        )

        # Simulate clip 1 completion and handoff to approval gate.
        advance_to_clip_1_review(job)
        self.store.save_job(job)
        self.store.append_event(
            job.id,
            "clip_1_ready_for_approval",
            {
                "status": job.status.value,
                "stage": job.stage.value,
                "attempt": message.attempt,
                "trace_id": message.trace_id,
            },
        )
        return job

    def resume_after_approval(self, job: Job) -> Job:
        max_attempts = int(os.getenv("VT_RETRY_MAX_ATTEMPTS", "3"))
        trace_id = str(uuid4())
        self.store.append_event(
            job.id,
            "pipeline_resumed_after_approval",
            {"status": job.status.value, "stage": job.stage.value, "trace_id": trace_id},
        )
        self.queue.enqueue(
            make_queue_message(
                job_id=job.id,
                task_type="continue_after_approval",
                task_key=f"{job.id}:continue_after_approval",
                trace_id=trace_id,
                attempt=1,
                max_attempts=max_attempts,
            )
        )
        return job

    def process_post_approval_pipeline(self, message: QueueMessage) -> Job | None:
        job = self.store.get_job(message.job_id)
        if not job:
            return None
        if not job.clip_1_approved:
            raise ValueError("Cannot continue pipeline before clip 1 approval")
        if job.status == JobStatus.DONE and job.stage == JobStage.DONE:
            telemetry.incr("worker.tasks.duplicate_ignored")
            self.store.append_event(
                job.id,
                "duplicate_task_ignored",
                {
                    "task_key": message.task_key,
                    "attempt": message.attempt,
                    "trace_id": message.trace_id,
                    "reason": "job already complete",
                },
            )
            return job

        # 20s => clip2 then assembly; 30s => clip2, clip3, assembly.
        job.status = JobStatus.RENDERING
        job.stage = JobStage.CLIP_2_GEN
        self.store.save_job(job)
        self.store.append_event(
            job.id,
            "clip_2_generation_started",
            {"status": job.status.value, "stage": job.stage.value, "trace_id": message.trace_id},
        )

        if job.clip_total == 3:
            job.stage = JobStage.CLIP_3_GEN
            self.store.save_job(job)
            self.store.append_event(
                job.id,
                "clip_3_generation_started",
                {"status": job.status.value, "stage": job.stage.value, "trace_id": message.trace_id},
            )

        job.stage = JobStage.ASSEMBLY
        self.store.save_job(job)
        self.store.append_event(
            job.id,
            "assembly_started",
            {"status": job.status.value, "stage": job.stage.value, "trace_id": message.trace_id},
        )

        job.stage = JobStage.DONE
        job.status = JobStatus.DONE
        self.store.save_job(job)
        self.store.append_event(
            job.id,
            "job_completed",
            {"status": job.status.value, "stage": job.stage.value, "trace_id": message.trace_id},
        )
        return job
