from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from backend.app.models import Job
from backend.app.queue import InMemoryTaskQueue
from backend.app.repository import InMemoryRepository
from backend.app.state_machine import approve_clip_1
from backend.app.worker_runner import process_message_once
from backend.app.worker import WorkerService


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_single_flow(format_seconds: int) -> dict[str, Any]:
    repo = InMemoryRepository()
    queue = InMemoryTaskQueue()
    worker = WorkerService(repo, queue)

    clip_total = 2 if format_seconds == 20 else 3
    job = Job(
        team_id="pilot-team",
        client_slug="pilot-client",
        format_seconds=format_seconds,
        clip_total=clip_total,
        idempotency_key=f"pilot-{format_seconds}",
    )
    repo.create_job(job)
    worker.enqueue_clip_1_generation(job)

    while True:
        message = queue.dequeue(timeout_seconds=1)
        if not message:
            break
        process_message_once(worker, repo, queue, message, retry_base_seconds=2)

    approval_target = repo.get_job(job.id)
    if not approval_target:
        raise RuntimeError("Pilot failure: job not found before approval")

    approve_clip_1(approval_target)
    repo.append_event(
        approval_target.id,
        "clip_1_approved",
        {
            "reviewer_user_id": "pilot-operator",
            "note": "Pilot approval",
            "status": approval_target.status.value,
            "stage": approval_target.stage.value,
        },
    )
    repo.save_job(approval_target)
    worker.resume_after_approval(approval_target)
    while True:
        message = queue.dequeue(timeout_seconds=1)
        if not message:
            break
        process_message_once(worker, repo, queue, message, retry_base_seconds=2)

    final_job = repo.get_job(job.id)
    if not final_job:
        raise RuntimeError("Pilot failure: final job not found")

    events = repo.list_events(job.id)
    event_types = [event.event_type for event in events]
    expected = {
        "job_created",
        "clip_1_generation_queued",
        "clip_1_generation_started",
        "clip_1_ready_for_approval",
        "clip_1_approved",
        "pipeline_resumed_after_approval",
        "clip_2_generation_started",
        "assembly_started",
        "job_completed",
    }
    if format_seconds == 30:
        expected.add("clip_3_generation_started")
    missing = sorted(expected.difference(set(event_types)))

    return {
        "format_seconds": format_seconds,
        "job_id": job.id,
        "clip_total": clip_total,
        "final_status": final_job.status.value,
        "final_stage": final_job.stage.value,
        "event_count": len(events),
        "event_types": event_types,
        "missing_expected_events": missing,
        "passed": len(missing) == 0 and final_job.status.value == "done" and final_job.stage.value == "done",
    }


def main() -> None:
    run_started_at = now_iso()
    result_20 = run_single_flow(20)
    result_30 = run_single_flow(30)
    overall_passed = result_20["passed"] and result_30["passed"]

    report = {
        "run_started_at": run_started_at,
        "run_finished_at": now_iso(),
        "overall_passed": overall_passed,
        "results": [result_20, result_30],
    }
    print(json.dumps(report, indent=2))

    if not overall_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
