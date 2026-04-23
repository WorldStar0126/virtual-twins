# First-Step Execution Brief (Pylyp)

## Context

This brief translates the 2026-04-20 meeting into an executable first phase.  
Goal: align stakeholders (Adam, Nick, Pylyp) on what should be built **now**, what should be deferred, and how success is measured.

---

## 1) What They Want From You (Directly)

Based on the transcript, they are asking for:

1. A **clear implementation plan** they can approve before coding further.
2. A practical **Phase 1 system** that improves current local workflow without overbuilding.
3. Product upgrades in the pipeline:
   - support optional **third generation loop** (20s -> 30s path)
   - keep **human-in-the-loop gate after clip 1**
   - support **end card pool rotation** instead of a single fixed ending
   - allow **configurable clip lengths** (default 10s, optional variants)
4. A direction for **employee interface + client approval flow**.
5. A foundation for:
   - cross-post publishing automation
   - analytics/tracking for sponsors
   - optimization memory (what prompt setups work/fail)

They explicitly requested a brief/plan from you before greenlighting next work.

---

## 2) Recommended First-Step Scope (What To Build Now)

## Phase 1 Objective

Build an **Operator Control Plane (MVP)** around the current generation engine so team members can reliably produce videos in batch with approvals and lower waste.

## In Scope (Immediate)

1. **Pipeline productization**
   - 2-clip and 3-clip modes
   - optional per-clip duration config (safe defaults)
   - deterministic run records for each job

2. **Human-in-loop checkpoint**
   - force review after Clip 1 before continuing
   - continue/reject/regenerate decisions captured in run history

3. **End card pool logic**
   - per-client end card set (4-5 variants)
   - rotate/shuffle selection policy
   - log which end card was used in each output

4. **Structured asset intake (lightweight)**
   - keep Google Drive for intake if needed
   - move approved assets into structured project storage model
   - enforce required folder conventions and metadata

5. **Run telemetry table (optimization seed)**
   - store prompt version, clip settings, retries, failures, cost estimate, approval outcome
   - this becomes the source for optimization agent later

## Out of Scope (For Later Phases)

- Full sponsor portal
- Full client self-serve SaaS onboarding
- Production-grade distributed auto-posting to every channel
- Fully autonomous self-learning agent actions without human oversight

---

## 3) Decision Principles (Senior-Level Guardrails)

1. **Default to safe reliability**  
   10s clip default, bounded template choices, controlled variation.

2. **Fail fast to save cost**  
   Mandatory review after clip 1 before additional generation.

3. **Template-first architecture**  
   5-6 video archetypes per industry, not unlimited free-form prompts.

4. **Data before intelligence**  
   Capture run history first; optimization agent comes after sufficient telemetry.

5. **Progressive migration**  
   Keep current local/script operations usable while introducing UI and structured storage.

---

## 4) First-Step System Design

## 4.1 Core Components (Phase 1)

1. **Operator UI (internal only)**
   - create job
   - choose client + template + duration mode (20s/30s)
   - attach/confirm references
   - review clip 1, approve continue
   - final approve and export

2. **Workflow API**
   - job state machine
   - orchestration endpoints
   - audit trail for approvals

3. **Worker Engine**
   - wraps existing toolchain:
     - upload
     - generate clip(s)
     - download
     - splice
     - append end card variant

4. **Run Ledger (DB)**
   - immutable run events
   - clip-level outcomes
   - retry + failure reasons
   - cost and timing estimates

5. **Storage Layer**
   - standardized client/listing/job paths
   - retain generated artifacts + selected references + metadata

---

## 4.2 Workflow State Model

Recommended canonical states:

- `draft`
- `assets_ready`
- `script_ready`
- `clip1_generating`
- `clip1_review_required`
- `clip1_approved` or `clip1_rejected`
- `clip2_generating`
- `clip3_generating` (optional)
- `assembly_pending`
- `final_review_required`
- `approved_for_publish`
- `published` (later integration)
- `failed`

This gives strong control for human review points and operational reporting.

---

## 5) First-Step Deliverables (What You Should Submit)

## Deliverable A: Approved Product Spec (short)

- Supported modes:
  - 20s (2 clips + optional end card)
  - 30s (3 clips + optional end card)
- Default clip duration: 10s
- Optional range: 4/5/10/15 with warning labels for higher failure risk
- Mandatory clip-1 review gate

## Deliverable B: Technical Design Doc (core)

- architecture diagram (logical)
- API contract outline
- state machine definition
- storage schema and path conventions
- run telemetry schema
- fallback/retry strategy

## Deliverable C: Iteration Plan (execution)

- sprint breakdown
- owners
- acceptance criteria
- risk mitigations

This current brief can serve as the foundation for B + C.

---

## 6) 4-Week Execution Plan (Practical)

## Week 1: Foundation + Contracts

- finalize product rules (20/30 modes, durations, end card pool behavior)
- define state machine and DB schema
- define template schema for prompt archetypes
- define asset folder and metadata conventions

**Exit criteria:**
- architecture + schema + workflow contracts signed off

## Week 2: Orchestration + Review Gate

- wire workflow API to current tools
- implement clip 1 manual approval checkpoint
- persist run telemetry per clip

**Exit criteria:**
- successful operator-run job with manual continue after clip 1

## Week 3: 30s Mode + End Card Pool

- add third-clip orchestration path
- add end card pool selection policy (rotate/shuffle)
- record selected end card and generation metadata

**Exit criteria:**
- one click flow can produce both 20s and 30s videos

## Week 4: Operator UX Hardening + Pilot

- lightweight operator dashboard for daily use
- run pilot batch with 2-3 real clients
- collect baseline metrics: success rate, retries, avg cost, throughput

**Exit criteria:**
- pilot report + go/no-go for broader rollout

---

## 7) Data You Must Capture From Day 1

For each generated clip and final video:

- client id, video template id, industry
- prompt version id and selected references
- clip duration and endpoint mode (fast/standard)
- retries and failure reason taxonomy
- moderation rejection flags
- human approval status/time
- estimated cost + elapsed time
- final publish target(s) (when enabled)

Without this, “self-learning” will remain theory.

---

## 8) Risk Register (Immediate)

1. **Model variability with longer clips**  
   Mitigation: default 10s, controlled 15s use, failure-aware UI warnings.

2. **Prompt inconsistency across operators**  
   Mitigation: template lock + parameterized prompts only.

3. **Poor asset quality from clients**  
   Mitigation: intake QA checklist and mandatory resubmission flags.

4. **Storage fragmentation (Drive/local/CDN)**  
   Mitigation: define canonical storage model now, even if ingestion remains hybrid.

5. **Overbuilding before telemetry exists**  
   Mitigation: prioritize run ledger and pilot results before advanced agent automation.

---

## 9) Recommended “First Reply” Back to Adam/Nick

Use this summary:

> I reviewed the meeting and propose a Phase 1 Operator Control Plane focused on reliable 20s/30s production with a mandatory clip-1 human review gate, end-card pool rotation, and full run telemetry capture.  
>  
> I’ll deliver this in a 4-week execution plan:  
> (1) contracts and schemas, (2) orchestration + review gate, (3) third-clip + end-card pool, (4) operator pilot and baseline metrics.  
>  
> This gives immediate production value now and creates the data foundation needed for later optimization agent and automated distribution.

---

## 10) Next Action Items For You (Pylyp)

1. Share this brief with Adam/Nick for approval.
2. Ask them to confirm 5 decisions:
   - default product packages (20 vs 30)
   - allowed clip durations in production
   - mandatory review policy details
   - end card pool selection rule
   - priority order: operator UI vs publishing automation
3. After approval, start Week 1 deliverables immediately.

---

## Final Note

Yes: they do need a **detailed plan**, but they need it in a **practical execution format**, not only a broad vision.  
This brief is built to be that execution baseline.

