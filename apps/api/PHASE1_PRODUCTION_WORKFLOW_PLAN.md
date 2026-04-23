# Phase 1 Implementation Plan (Production Workflow)

## Executive Objective

Deliver a production-ready internal workflow that reliably generates 20s and 30s videos with controlled quality, lower credit waste, and clear operational accountability.

This phase prioritizes **execution reliability** over platform breadth.

---

## 1) Strategic Scope

## In Scope (Phase 1)

1. **Configurable generation workflow**
   - 20s mode: 2 clips + end card
   - 30s mode: 3 clips + end card
   - default clip duration: 10s for reliability
   - optional per-clip durations: 4/5/10/15 (guard-railed)

2. **Human-in-the-loop quality gate**
   - mandatory review after clip 1
   - no downstream generation (clip 2/3) without approval
   - explicit decision outcomes: approve, regenerate, reject

3. **End card pool orchestration**
   - per-client/sponsor pool of approved end cards
   - deterministic rotation policy (round-robin) or controlled random
   - usage logging per final output

4. **Operational run ledger**
   - record each run and clip-level events
   - capture retries, failure reasons, approval actions, duration, and cost estimate
   - produce auditability for quality and sponsor reporting foundation

5. **Structured asset readiness**
   - retain Google Drive as intake channel (short-term)
   - enforce normalized production layout inside pipeline storage
   - standardize references required for reliable generation

## Explicitly Out of Scope (Phase 2+)

- Full client self-serve portal
- Full cross-post distribution automation to all social channels
- Sponsor analytics dashboard with channel-level engagement aggregation
- Fully autonomous optimization agent without human oversight

---

## 2) Product Operating Model

## Job Types

- `standard_20s`: clip1 + clip2 + end card
- `extended_30s`: clip1 + clip2 + clip3 + end card

## Governance Defaults

- 10s clip default for production stability
- 15s allowed only for low-motion templates with operator warning
- template-first prompting (bounded archetypes), not free-form by default
- mandatory first-clip approval checkpoint for cost containment

---

## 3) Workflow State Machine (Canonical)

- `draft`
- `assets_validated`
- `script_approved`
- `clip1_generating`
- `clip1_review_required`
- `clip1_approved` or `clip1_rejected`
- `clip2_generating`
- `clip3_generating` (optional for 30s mode)
- `assembly_pending`
- `final_review_required`
- `approved_for_delivery`
- `failed`

This state model is non-negotiable for operational clarity, event replay, and KPI reporting.

---

## 4) Technical Implementation (Current Repo Aligned)

## Existing toolchain to orchestrate

- `tools/upload_assets.py`
- `tools/generate_video.py`
- `tools/download_video.py`
- `tools/splice_clips.py`
- `tools/generate_end_card.py`
- `tools/extract_best_frame.py` (used when continuity is required)

## New Phase 1 orchestration layer

Create a thin orchestration controller (CLI-first) that:

1. Loads a run config (client, mode, clip durations, template, references, end-card policy).
2. Executes clip 1.
3. Pauses at review gate and waits for explicit human decision.
4. Continues clip 2/3 only after approval.
5. Splices clips and appends selected end card.
6. Writes a complete run ledger record and output manifest.

No heavy web application is required for Phase 1 delivery.

---

## 5) Data Contracts (Minimum Required)

## Run Config (input contract)

- `run_id`
- `client_slug`
- `job_type` (`standard_20s` | `extended_30s`)
- `clip_plan` (ordered list with per-clip duration and prompt/template metadata)
- `continuity_mode` (`new_scene` | `carry_forward_frame`)
- `end_card_policy` (`round_robin` | `random_seeded`)
- `operator_id`

## Run Ledger (output contract)

- run-level: start/end timestamps, total elapsed, status, total retries, estimated cost
- clip-level: seed, settings, selected references, attempt count, failure reason (if any)
- review-level: approver, decision, notes, decision timestamp
- assembly-level: clip file manifest, end-card id selected, final output path

---

## 6) Reliability and Cost Controls

1. **Fail-fast control**
   - hard stop after clip 1 until approved

2. **Template guardrails**
   - permit only curated video archetypes in production mode

3. **Duration risk policy**
   - default 10s, warn at 15s, enforce operator acknowledgement

4. **Retry discipline**
   - bounded retry count per clip
   - mandatory failure reason classification before retry

5. **Continuity policy**
   - use `extract_best_frame.py` only when continuity is required
   - avoid unnecessary frame-carry costs for hard cut scene transitions

---

## 7) Delivery Plan (Accelerated)

## Week 1 — Core Orchestration + Gate

- implement job config schema and validation
- implement workflow runner for 20s and 30s modes
- implement clip 1 approval checkpoint
- implement run ledger write path

**Exit Criteria**
- at least one successful 20s and one successful 30s run in controlled test
- clip 1 gate blocks downstream generation until explicit approval

## Week 2 — End Card Pool + Pilot Hardening

- implement end-card pool selection policy
- finalize output manifest + event trail for every run
- pilot with selected internal operators on real client jobs
- tune retry and template defaults based on observed failures

**Exit Criteria**
- stable internal workflow for daily production
- measurable reduction in wasted generations from gate enforcement
- approved pilot handoff for broader operator usage

---

## 8) Acceptance Criteria (Client-Visible)

Phase 1 is considered complete when:

1. Team can execute both 20s and 30s jobs through one controlled workflow.
2. First-clip human approval is enforced and auditable.
3. End card selection rotates from approved pool and is logged.
4. Every run has traceable records (settings, retries, outcomes, artifacts).
5. Pilot demonstrates operational readiness for scaled internal use.

---

## 9) Risks and Mitigations

1. **Model instability at longer durations**
   - Mitigation: default 10s + template constraints + warnings for 15s usage

2. **Credit waste from bad early outputs**
   - Mitigation: mandatory clip 1 gate before continuing

3. **Inconsistent operator behavior**
   - Mitigation: standardized run config schema + state machine + audit trail

4. **Asset quality variance**
   - Mitigation: strict intake checklist and reference validation before run start

---

## 10) Immediate Next Actions

1. Approve this Phase 1 scope and acceptance criteria.
2. Confirm default policies:
   - end card policy (`round_robin` recommended)
   - max retry per clip
   - approver roles for clip 1 gate
3. Begin Week 1 implementation and provide mid-week checkpoint demo.

---

## 11) Engineering Architecture (Phase 1)

## System boundaries

- **Orchestrator (new):** stateful run controller that calls existing tools in deterministic order.
- **Tool adapters (new):** thin wrappers around current scripts for typed I/O and consistent error mapping.
- **Ledger store (new):** append-only run event log plus run summary index.
- **Artifacts (existing + standardized):** clips, final videos, manifests, and metadata under deterministic paths.
- **Operator surface (Phase 1):** CLI commands + JSON review decision file (no full web app required).

## Runtime flow

1. Validate run config.
2. Resolve assets and references.
3. Generate clip 1.
4. Block for review decision.
5. Continue clip 2/3 or branch to regenerate/reject.
6. Splice approved clips.
7. Select end card variant and append.
8. Emit final manifest and ledger events.

## Failure domains

- **Provider errors:** fal timeout, queue failure, payload rejection.
- **Asset errors:** missing references, invalid media formats, empty audio.
- **Assembly errors:** ffmpeg concat mismatch, missing clip outputs.
- **Workflow errors:** invalid state transition or missing review action.

Each failure must map to a typed code for reporting and retries.

---

## 12) Proposed File/Module Layout

Add the following internal modules (under `tools/` or a new `pipeline/` package):

- `pipeline/orchestrator.py` - core run state machine executor
- `pipeline/contracts.py` - typed models for config, events, manifests
- `pipeline/state_machine.py` - allowed transitions + transition validator
- `pipeline/tool_adapters.py` - wrappers for upload/generate/download/splice/end-card
- `pipeline/review_gate.py` - human decision wait/resolve logic
- `pipeline/endcard_selector.py` - round-robin/random-seeded strategy
- `pipeline/ledger.py` - append event + build run summary
- `pipeline/errors.py` - normalized error codes and retry policy
- `pipeline/cli.py` - operator commands (`start-run`, `approve-run`, `retry-clip`, `finalize-run`)

Recommended artifacts layout:

- `.runs/{run_id}/run_config.json`
- `.runs/{run_id}/events.jsonl`
- `.runs/{run_id}/review/clip1_decision.json`
- `.runs/{run_id}/manifests/final_manifest.json`
- `output/{client_slug}/{run_id}/clips/*.mp4`
- `output/{client_slug}/{run_id}/final/*.mp4`

---

## 13) Schemas (Concrete)

## `run_config.json` (minimum)

```json
{
  "run_id": "20260421_james_001",
  "client_slug": "james-duffer",
  "job_type": "extended_30s",
  "operator_id": "op_01",
  "clip_plan": [
    {
      "clip_index": 1,
      "duration": 10,
      "template_id": "realtor_market_update_v1",
      "prompt": "..."
    },
    {
      "clip_index": 2,
      "duration": 10,
      "template_id": "realtor_market_update_v1",
      "prompt": "...",
      "continuity_mode": "carry_forward_frame"
    },
    {
      "clip_index": 3,
      "duration": 10,
      "template_id": "realtor_market_update_v1",
      "prompt": "...",
      "continuity_mode": "new_scene"
    }
  ],
  "generation_defaults": {
    "resolution": "720p",
    "aspect_ratio": "9:16",
    "fast": false,
    "max_retries_per_clip": 2
  },
  "end_card_policy": {
    "mode": "round_robin",
    "pool_id": "sponsor_pool_a"
  }
}
```

## `events.jsonl` (append-only ledger)

Each event record:

- `event_id`, `run_id`, `timestamp_utc`
- `event_type` (e.g., `clip_generation_started`, `clip_review_decided`)
- `state_from`, `state_to`
- `payload` (typed details by event)

Example event types:

- `run_created`
- `assets_validated`
- `clip_generation_started`
- `clip_generation_succeeded`
- `clip_generation_failed`
- `clip_review_requested`
- `clip_review_decided`
- `assembly_started`
- `assembly_succeeded`
- `run_completed`
- `run_failed`

## `final_manifest.json`

- run metadata (client, operator, timings, status)
- clip outputs (path, seed, duration, retries)
- end-card selection details
- final asset paths
- cost estimate summary

---

## 14) Orchestration Algorithm (Deterministic)

## Pseudocode

```python
def execute_run(config):
    validate_config(config)
    run = create_run(config)
    emit("run_created")
    validate_assets(run)
    emit("assets_validated")

    for clip in config.clip_plan:
        while clip.attempts <= max_retries:
            emit("clip_generation_started", clip=clip.index, attempt=clip.attempts)
            result = generate_clip(clip, run)
            if result.ok:
                persist_clip(result)
                emit("clip_generation_succeeded", clip=clip.index, seed=result.seed)
                break
            emit("clip_generation_failed", clip=clip.index, reason=result.error_code)
            clip.attempts += 1
        if not result.ok:
            fail_run("clip_generation_exhausted")
            return

        if clip.index == 1:
            emit("clip_review_requested")
            decision = wait_for_review_decision(run.run_id)
            emit("clip_review_decided", decision=decision.type)
            if decision.type == "reject":
                fail_run("rejected_after_clip1")
                return
            if decision.type == "regenerate":
                reset_clip(clip.index)
                continue

    emit("assembly_started")
    final = assemble_clips_and_endcard(run)
    if not final.ok:
        fail_run(final.error_code)
        return

    emit("assembly_succeeded", final_path=final.path)
    complete_run(final)
    emit("run_completed")
```

## State transition guard

All transitions must be validated through a transition table to prevent invalid paths (e.g., `clip2_generating` before `clip1_approved`).

---

## 15) Interface Contracts (CLI-First)

## Commands

- `python -m pipeline.cli start-run --config configs/run_001.json`
- `python -m pipeline.cli review-run --run-id <id> --decision approve --notes "..."`
- `python -m pipeline.cli review-run --run-id <id> --decision regenerate --target clip1`
- `python -m pipeline.cli retry-clip --run-id <id> --clip 2 --reason "..."`
- `python -m pipeline.cli finalize-run --run-id <id>`
- `python -m pipeline.cli run-status --run-id <id>`

## Review decision contract

`review/clip1_decision.json`:

```json
{
  "run_id": "20260421_james_001",
  "clip_index": 1,
  "decision": "approve",
  "approver_id": "qa_02",
  "notes": "Lip sync acceptable, proceed.",
  "timestamp_utc": "2026-04-21T16:55:10Z"
}
```

---

## 16) Test Strategy (Production Workflow)

## Unit tests

- config schema validation
- state transition validation
- retry policy behavior
- end-card selection strategy determinism
- error code normalization

## Integration tests

- 20s happy path (2 clips + end card)
- 30s happy path (3 clips + end card)
- clip1 reject flow
- clip1 regenerate flow
- clip2 retry then success flow
- assembly failure handling flow

## Operational acceptance tests

- test with at least 2 clients and 2 templates
- verify ledger completeness for every run
- verify reproducibility with fixed seed runs
- compare cost and failure metrics before/after gate

## KPIs to track from day 1

- first-pass success rate (clip-level, run-level)
- average retries per clip
- rejection rate at clip1 gate
- average runtime per completed run
- estimated cost per delivered video

---

## 17) Phase 1 Definition of Done (Technical)

Phase 1 is technically complete when all conditions are true:

1. State-machine orchestrator supports 20s and 30s modes in production.
2. Clip1 review gate is hard-enforced and auditable in events.
3. End card selection policy is configurable and recorded in manifest.
4. Every run produces `events.jsonl` and `final_manifest.json`.
5. Retry/failure handling uses typed error codes and bounded retries.
6. Integration test suite covers primary happy and failure paths.
7. Pilot batch demonstrates stable operations with measurable waste reduction.

