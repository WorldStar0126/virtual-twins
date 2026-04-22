from __future__ import annotations

import json
from datetime import datetime, timezone

from backend.scripts.run_internal_pilot import run_single_flow


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    started = now_iso()
    runs = []
    for i in range(50):
        runs.append(run_single_flow(20 if i % 2 == 0 else 30))

    total = len(runs)
    completed = sum(1 for r in runs if r["passed"])
    completion_rate = (completed / total) * 100.0 if total else 0.0
    gate_enforcement_failures = sum(
        1
        for r in runs
        if ("clip_2_generation_started" in r["event_types"] and "clip_1_approved" not in r["event_types"])
    )
    retry_failure_visibility_failures = sum(
        1
        for r in runs
        if "job_completed" not in r["event_types"] and not any(
            evt in r["event_types"] for evt in {"task_retry_scheduled", "task_failed_terminal", "job_failed"}
        )
    )

    report = {
        "run_started_at": started,
        "run_finished_at": now_iso(),
        "total_jobs": total,
        "completed_jobs": completed,
        "completion_rate_percent": round(completion_rate, 2),
        "clip_1_gate_enforcement_failures": gate_enforcement_failures,
        "retry_failure_visibility_failures": retry_failure_visibility_failures,
        "phase_1_exit_criteria": {
            "completion_rate_95_plus": completion_rate >= 95.0,
            "clip_1_gate_enforced_100_percent": gate_enforcement_failures == 0,
            "retry_failures_visible": retry_failure_visibility_failures == 0,
        },
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
