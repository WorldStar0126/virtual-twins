from __future__ import annotations

from backend.app.models import Job, JobStage, JobStatus


class InvalidTransitionError(ValueError):
    """Raised when a job transition is invalid for current stage."""


def advance_to_clip_1_review(job: Job) -> Job:
    if job.stage not in {JobStage.ASSET_UPLOAD, JobStage.CLIP_1_GEN}:
        raise InvalidTransitionError(
            f"Cannot move to clip_1_review from stage={job.stage.value}"
        )
    job.status = JobStatus.AWAITING_APPROVAL
    job.stage = JobStage.CLIP_1_REVIEW
    return job


def approve_clip_1(job: Job) -> Job:
    if job.stage != JobStage.CLIP_1_REVIEW:
        raise InvalidTransitionError(
            f"Clip 1 can only be approved from stage={JobStage.CLIP_1_REVIEW.value}"
        )
    job.clip_1_approved = True
    job.status = JobStatus.RENDERING
    job.stage = JobStage.CLIP_2_GEN
    return job


def reject_clip_1(job: Job) -> Job:
    if job.stage != JobStage.CLIP_1_REVIEW:
        raise InvalidTransitionError(
            f"Clip 1 can only be rejected from stage={JobStage.CLIP_1_REVIEW.value}"
        )
    job.clip_1_approved = False
    job.status = JobStatus.FAILED
    job.stage = JobStage.CLIP_1_REVIEW
    return job
