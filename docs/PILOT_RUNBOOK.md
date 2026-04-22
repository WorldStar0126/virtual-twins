# Internal Pilot Runbook (Phase 1)

This runbook validates the first internal pilot requirement from `PROJECT_PLAN.md`:

- Run 20s flow
- Run 30s flow
- Confirm approval gate + deterministic run event visibility

## Preconditions

- Python environment active
- Dependencies installed:

```bash
pip install -r backend/requirements.txt
```

## Execute pilot harness

From repository root:

```bash
python -m backend.scripts.run_internal_pilot
```

The script runs both flows and prints a JSON report.

## Pass criteria for this harness

For each flow (20s and 30s):

- Job is created
- Clip 1 is queued
- Clip 1 generation starts
- Clip 1 moves to review gate
- Clip 1 approval is recorded
- Pipeline resumes after approval

Expected event sequence set:

- `job_created`
- `clip_1_generation_queued`
- `clip_1_generation_started`
- `clip_1_ready_for_approval`
- `clip_1_approved`
- `pipeline_resumed_after_approval`

## Interpreting output

- `overall_passed: true` means both 20s and 30s pilot checks passed.
- `missing_expected_events` lists any required events that were not generated.

## Notes

- This harness currently runs in-memory for deterministic validation.
- For staging pilot, run equivalent checks through API + Redis + PostgreSQL and archive reports.
