from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CreateJobRequest(BaseModel):
    client_slug: str = Field(min_length=1)
    format_seconds: Literal[20, 30]
    created_by: str | None = None
    idempotency_key: str | None = None


class CreateJobResponse(BaseModel):
    id: str
    client_slug: str
    format_seconds: int
    status: str
    stage: str
    clip_total: int
    created_at: datetime
    idempotency_replayed: bool = False


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class ClipApprovalRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    reviewer_user_id: str | None = None
    note: str | None = None


class JobEventResponse(BaseModel):
    id: str
    job_id: str
    event_type: str
    trace_id: str
    payload: dict[str, Any]
    created_at: datetime


class StartGoogleOAuthRequest(BaseModel):
    pass


class StartGoogleOAuthResponse(BaseModel):
    state: str
    authorize_url: str


class CompleteGoogleOAuthResponse(BaseModel):
    source_id: str
    provider: str
    external_account_id: str
    created_at: datetime


class StartGoogleSyncRequest(BaseModel):
    source_id: str = Field(min_length=1)
    folder_id: str = Field(min_length=1)
    page_token: str | None = None


class GoogleSyncJobResponse(BaseModel):
    sync_job_id: str
    source_id: str
    status: str
    synced_count: int
    next_page_token: str | None
    error_message: str | None
    started_at: datetime
    ended_at: datetime | None


class AuthSignupRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1)


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)


class AuthRefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=16)


class AuthLogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=16)


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user_id: str
    role: str
