from __future__ import annotations

import logging
import hashlib
import time
import os
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Response, status
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.auth import AuthService
from backend.app.auth_store import build_auth_store
from backend.app.connector_store import build_connector_store
from backend.app.connectors import ConnectorService, GoogleDriveConnector
from backend.app.models import Job
from backend.app.observability import telemetry
from backend.app.queue import build_task_queue
from backend.app.repository import build_repository
from backend.app.schemas import (
    ClipApprovalRequest,
    CompleteGoogleOAuthResponse,
    CreateJobRequest,
    CreateJobResponse,
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthRefreshRequest,
    AuthSignupRequest,
    AuthTokenResponse,
    GoogleSyncJobResponse,
    JobEventResponse,
    StartGoogleOAuthRequest,
    StartGoogleOAuthResponse,
    StartGoogleSyncRequest,
)
from backend.app.state_machine import InvalidTransitionError, approve_clip_1, reject_clip_1
from backend.app.worker import WorkerService

app = FastAPI(title="Virtual Twins API", version="0.1.0")
store = build_repository()
task_queue = build_task_queue()
worker = WorkerService(store, task_queue)
connector_service = ConnectorService(GoogleDriveConnector(), build_connector_store())
auth_service = AuthService()
auth_store = build_auth_store()
logger = logging.getLogger("vt.api")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

DEMO_EMAIL = "demo@vt.local"
DEMO_PASSWORD = "StrongPass123!"
DEMO_USER_ID = "demo-user-1"
DEMO_ROLE = "owner"

cors_origins = os.getenv("VT_CORS_ORIGINS", "*")
allow_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
allow_all_origins = "*" in allow_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins or not allow_origins else allow_origins,
    # Auth uses Bearer tokens in headers, not browser cookies.
    # Keeping this False allows wildcard CORS for local prototyping.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def error_response(status_code: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "HTTP error"
    return error_response(
        status_code=exc.status_code,
        code=f"http_{exc.status_code}",
        message=message,
        details={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_error",
        message="Request validation failed",
        details={"errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", extra={"error": str(exc)})
    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        message="Internal server error",
        details={},
    )


def _extract_bearer_token(request: Request) -> str:
    raw = request.headers.get("authorization", "")
    if not raw.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = raw.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return token


def _get_current_actor(request: Request) -> dict:
    token = _extract_bearer_token(request)
    try:
        claims = auth_service.parse_access_token(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc
    return {"user_id": claims.user_id, "role": claims.role}


def _require_roles(request: Request, allowed_roles: set[str]) -> dict:
    actor = _get_current_actor(request)
    if actor["role"] not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return actor


def _issue_auth_tokens(user_id: str, role: str) -> AuthTokenResponse:
    access_token, access_expires = auth_service.issue_access_token(user_id=user_id, role=role)  # type: ignore[arg-type]
    refresh_token, refresh_hash, refresh_expires = auth_service.issue_refresh_token()
    auth_store.store_refresh_token(
        user_id=user_id,
        token_hash=refresh_hash,
        expires_at=refresh_expires,
    )
    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=access_expires,
        user_id=user_id,
        role=role,
    )


@app.middleware("http")
async def metrics_and_logging_middleware(request: Request, call_next):
    started = time.perf_counter()
    request_id = str(uuid4())
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        status_code = response.status_code if response else 500
        telemetry.incr("api.requests.total")
        telemetry.observe_ms("api.requests.latency", elapsed_ms)
        status_bucket = f"{status_code // 100}xx"
        telemetry.incr(f"api.requests.{status_bucket}")
        if status_code >= 500:
            telemetry.incr("api.requests.5xx")
        logger.info(
            "api_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "latency_ms": round(elapsed_ms, 2),
            },
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict:
    return telemetry.snapshot()


@app.get("/v1/ops/alerts")
def alert_status() -> dict:
    alerts = telemetry.evaluate_alerts()
    return {"alerts": alerts, "count": len(alerts)}


@app.post("/v1/auth/signup", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def auth_signup(payload: AuthSignupRequest) -> AuthTokenResponse:
    _ = payload
    return _issue_auth_tokens(user_id=DEMO_USER_ID, role=DEMO_ROLE)


@app.post("/v1/auth/login", response_model=AuthTokenResponse)
def auth_login(payload: AuthLoginRequest) -> AuthTokenResponse:
    email = payload.email.lower().strip()
    if email != DEMO_EMAIL or payload.password != DEMO_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _issue_auth_tokens(user_id=DEMO_USER_ID, role=DEMO_ROLE)


@app.post("/v1/auth/refresh", response_model=AuthTokenResponse)
def auth_refresh(payload: AuthRefreshRequest) -> AuthTokenResponse:
    token_hash = hashlib.sha256(payload.refresh_token.encode("utf-8")).hexdigest()
    refresh = auth_store.get_refresh_token(token_hash)
    if not refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    auth_store.revoke_refresh_token(token_hash)
    return _issue_auth_tokens(user_id=DEMO_USER_ID, role=DEMO_ROLE)


@app.post("/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def auth_logout(payload: AuthLogoutRequest) -> Response:
    token_hash = hashlib.sha256(payload.refresh_token.encode("utf-8")).hexdigest()
    auth_store.revoke_refresh_token(token_hash)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/v1/jobs", response_model=CreateJobResponse, status_code=status.HTTP_201_CREATED)
def create_job(payload: CreateJobRequest, response: Response, request: Request) -> CreateJobResponse:
    _require_roles(request, {"owner", "admin", "operator"})
    if payload.idempotency_key:
        existing = store.get_job_by_idempotency(payload.idempotency_key)
        if existing:
            response.status_code = status.HTTP_200_OK
            return CreateJobResponse(
                id=existing.id,
                client_slug=existing.client_slug,
                format_seconds=existing.format_seconds,
                status=existing.status.value,
                stage=existing.stage.value,
                clip_total=existing.clip_total,
                created_at=existing.created_at,
                idempotency_replayed=True,
            )

    clip_total = 2 if payload.format_seconds == 20 else 3
    job = Job(
        client_slug=payload.client_slug,
        format_seconds=payload.format_seconds,
        created_by=payload.created_by,
        idempotency_key=payload.idempotency_key,
        clip_total=clip_total,
    )
    job = store.create_job(job)
    worker.enqueue_clip_1_generation(job)
    return CreateJobResponse(
        id=job.id,
        client_slug=job.client_slug,
        format_seconds=job.format_seconds,
        status=job.status.value,
        stage=job.stage.value,
        clip_total=job.clip_total,
        created_at=job.created_at,
        idempotency_replayed=False,
    )


@app.post("/v1/jobs/{job_id}/approvals/clip-1", response_model=CreateJobResponse)
def submit_clip_1_approval(job_id: str, payload: ClipApprovalRequest, request: Request) -> CreateJobResponse:
    _require_roles(request, {"owner", "admin", "operator"})
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    try:
        if payload.decision == "approved":
            approve_clip_1(job)
            store.append_event(
                job.id,
                "clip_1_approved",
                {
                    "reviewer_user_id": payload.reviewer_user_id,
                    "note": payload.note,
                    "status": job.status.value,
                    "stage": job.stage.value,
                },
            )
            worker.resume_after_approval(job)
        else:
            reject_clip_1(job)
            store.append_event(
                job.id,
                "clip_1_rejected",
                {
                    "reviewer_user_id": payload.reviewer_user_id,
                    "note": payload.note,
                    "status": job.status.value,
                    "stage": job.stage.value,
                },
            )
        store.save_job(job)
    except InvalidTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return CreateJobResponse(
        id=job.id,
        client_slug=job.client_slug,
        format_seconds=job.format_seconds,
        status=job.status.value,
        stage=job.stage.value,
        clip_total=job.clip_total,
        created_at=job.created_at,
    )


@app.get("/v1/jobs/{job_id}/events", response_model=list[JobEventResponse])
def fetch_run_event_history(job_id: str, request: Request) -> list[JobEventResponse]:
    _require_roles(request, {"owner", "admin", "operator", "viewer"})
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    events = store.list_events(job_id)
    return [
        JobEventResponse(
            id=e.id,
            job_id=e.job_id,
            event_type=e.event_type,
            trace_id=e.trace_id,
            payload=e.payload,
            created_at=e.created_at,
        )
        for e in events
    ]


@app.post(
    "/v1/connectors/google-drive/oauth/start",
    response_model=StartGoogleOAuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_google_oauth(payload: StartGoogleOAuthRequest, request: Request) -> StartGoogleOAuthResponse:
    _require_roles(request, {"owner", "admin", "operator"})
    state, authorize_url = connector_service.start_oauth()
    return StartGoogleOAuthResponse(state=state, authorize_url=authorize_url)


@app.get(
    "/v1/connectors/google-drive/oauth/callback",
    response_model=CompleteGoogleOAuthResponse,
)
def complete_google_oauth(code: str, state: str) -> CompleteGoogleOAuthResponse:
    try:
        source = connector_service.complete_oauth(state=state, code=code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CompleteGoogleOAuthResponse(
        source_id=source.id,
        provider=source.provider,
        external_account_id=source.external_account_id,
        created_at=source.created_at,
    )


@app.post(
    "/v1/connectors/google-drive/sync",
    response_model=GoogleSyncJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_google_drive_sync(payload: StartGoogleSyncRequest, request: Request) -> GoogleSyncJobResponse:
    _require_roles(request, {"owner", "admin", "operator"})
    try:
        sync_job = connector_service.start_incremental_sync(
            source_id=payload.source_id,
            folder_id=payload.folder_id,
            page_token=payload.page_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return GoogleSyncJobResponse(
        sync_job_id=sync_job.id,
        source_id=sync_job.source_id,
        status=sync_job.status,
        synced_count=sync_job.synced_count,
        next_page_token=sync_job.next_page_token,
        error_message=sync_job.error_message,
        started_at=sync_job.started_at,
        ended_at=sync_job.ended_at,
    )


@app.get("/v1/connectors/google-drive/sync/{sync_job_id}", response_model=GoogleSyncJobResponse)
def get_google_drive_sync(sync_job_id: str, request: Request) -> GoogleSyncJobResponse:
    _require_roles(request, {"owner", "admin", "operator", "viewer"})
    sync_job = connector_service.get_sync_job(sync_job_id)
    if not sync_job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sync job not found")
    return GoogleSyncJobResponse(
        sync_job_id=sync_job.id,
        source_id=sync_job.source_id,
        status=sync_job.status,
        synced_count=sync_job.synced_count,
        next_page_token=sync_job.next_page_token,
        error_message=sync_job.error_message,
        started_at=sync_job.started_at,
        ended_at=sync_job.ended_at,
    )
