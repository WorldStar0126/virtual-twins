from __future__ import annotations

import os
import time

from backend.app.models import JobStatus
from backend.app.observability import telemetry
from backend.app.queue import QueueMessage, build_task_queue
from backend.app.repository import build_repository
from backend.app.worker import WorkerService


def process_message_once(worker: WorkerService, store: object, queue: object, message: QueueMessage, retry_base_seconds: int) -> None:
    if message.task_type not in {"generate_clip_1", "continue_after_approval"}:
        return
    started = time.perf_counter()
    telemetry.incr("worker.tasks.total")
    try:
        if message.task_type == "generate_clip_1":
            worker.process_clip_1_generation(message)
        else:
            worker.process_post_approval_pipeline(message)
        telemetry.incr("worker.tasks.success")
    except Exception as exc:  # pragma: no cover - runtime safety path
        telemetry.incr("worker.tasks.failure")
        job = store.get_job(message.job_id)
        if message.attempt < message.max_attempts:
            next_attempt = message.attempt + 1
            delay_seconds = retry_base_seconds * (2 ** (message.attempt - 1))
            queue.enqueue(
                message=type(message)(
                    message_id=message.message_id,
                    job_id=message.job_id,
                    task_type=message.task_type,
                    task_key=message.task_key,
                    trace_id=message.trace_id,
                    attempt=next_attempt,
                    max_attempts=message.max_attempts,
                ),
                delay_seconds=delay_seconds,
            )
            telemetry.incr("worker.task_retry_scheduled")
            if job:
                store.append_event(
                    message.job_id,
                    "task_retry_scheduled",
                    {
                        "task_key": message.task_key,
                        "attempt": message.attempt,
                        "next_attempt": next_attempt,
                        "delay_seconds": delay_seconds,
                        "trace_id": message.trace_id,
                        "error": str(exc),
                    },
                )
            return

        queue.enqueue_dead_letter(message=message, reason=str(exc))
        telemetry.incr("worker.task_failed_terminal")
        if job:
            job.status = JobStatus.FAILED
            store.save_job(job)
            store.append_event(
                message.job_id,
                "task_failed_terminal",
                {
                    "task_key": message.task_key,
                    "attempt": message.attempt,
                    "trace_id": message.trace_id,
                    "error": str(exc),
                },
            )
            store.append_event(
                message.job_id,
                "job_failed",
                {"status": job.status.value, "stage": job.stage.value},
            )
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        telemetry.observe_ms("worker.tasks.latency", elapsed_ms)


def run_worker_loop(poll_timeout_seconds: int = 5) -> None:
    retry_base_seconds = int(os.getenv("VT_RETRY_BASE_SECONDS", "2"))
    store = build_repository()
    queue = build_task_queue()
    worker = WorkerService(store, queue)

    while True:
        message = queue.dequeue(timeout_seconds=poll_timeout_seconds)
        if not message:
            continue
        process_message_once(worker, store, queue, message, retry_base_seconds)


if __name__ == "__main__":
    run_worker_loop()
