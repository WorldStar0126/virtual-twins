from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import uuid4

import requests


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AssetRecord:
    asset_id: str
    external_id: str
    name: str
    mime_type: str
    modified_time: str
    web_view_link: str


@dataclass
class SyncJob:
    id: str
    source_id: str
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    synced_count: int = 0
    next_page_token: str | None = None
    error_message: str | None = None


class AssetConnector(Protocol):
    provider: str

    def build_oauth_authorize_url(self, state: str) -> str: ...
    def exchange_code(self, code: str) -> "ConnectorTokens": ...
    def refresh_access_token(self, refresh_token: str) -> "ConnectorTokens": ...
    def scan_folder(self, access_token: str, folder_id: str, page_token: str | None = None) -> tuple[list[AssetRecord], str | None]: ...


class ConnectorStore(Protocol):
    def save_oauth_state(self, state: str, provider: str) -> None: ...
    def pop_oauth_state(self, state: str) -> str | None: ...
    def create_source(self, source: "ConnectorSource") -> "ConnectorSource": ...
    def update_source_tokens(
        self, source_id: str, access_token: str, refresh_token: str | None, expires_at: datetime | None
    ) -> "ConnectorSource" | None: ...
    def get_source(self, source_id: str) -> "ConnectorSource" | None: ...
    def create_sync_job(self, sync_job: "SyncJob") -> "SyncJob": ...
    def update_sync_job(self, sync_job: "SyncJob") -> "SyncJob": ...
    def get_sync_job(self, sync_job_id: str) -> "SyncJob" | None: ...
    def upsert_assets(self, source_id: str, assets: list[AssetRecord]) -> int: ...


@dataclass
class ConnectorTokens:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None


class GoogleDriveConnector:
    provider = "google_drive"

    def __init__(self) -> None:
        self.client_id = os.getenv("GOOGLE_CLIENT_ID", "set-google-client-id")
        self.redirect_uri = os.getenv(
            "GOOGLE_REDIRECT_URI",
            "http://localhost:8000/v1/connectors/google-drive/oauth/callback",
        )
        self.scope = "https://www.googleapis.com/auth/drive.readonly"
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.token_url = "https://oauth2.googleapis.com/token"
        self.files_url = "https://www.googleapis.com/drive/v3/files"

    def build_oauth_authorize_url(self, state: str) -> str:
        return (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            "&response_type=code"
            f"&scope={self.scope}"
            "&access_type=offline"
            "&prompt=consent"
            f"&state={state}"
        )

    def exchange_code(self, code: str) -> ConnectorTokens:
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        response = requests.post(self.token_url, data=payload, timeout=20)
        if response.status_code != 200:
            raise ValueError(f"OAuth token exchange failed: {response.text}")
        data = response.json()
        expires_at = None
        if "expires_in" in data:
            expires_at = utcnow() + timedelta(seconds=int(data["expires_in"]))
        return ConnectorTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
        )

    def refresh_access_token(self, refresh_token: str) -> ConnectorTokens:
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        response = requests.post(self.token_url, data=payload, timeout=20)
        if response.status_code != 200:
            raise ValueError(f"OAuth refresh failed: {response.text}")
        data = response.json()
        expires_at = None
        if "expires_in" in data:
            expires_at = utcnow() + timedelta(seconds=int(data["expires_in"]))
        return ConnectorTokens(
            access_token=data["access_token"],
            refresh_token=refresh_token,
            expires_at=expires_at,
        )

    def scan_folder(
        self, access_token: str, folder_id: str, page_token: str | None = None
    ) -> tuple[list[AssetRecord], str | None]:
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,webViewLink)",
            "pageSize": 100,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        if page_token:
            params["pageToken"] = page_token

        response = requests.get(self.files_url, headers=headers, params=params, timeout=20)
        if response.status_code in (401, 403):
            raise PermissionError("Google Drive access token invalid or expired")
        if response.status_code != 200:
            raise ValueError(f"Drive scan failed: {response.text}")

        body = response.json()
        assets: list[AssetRecord] = []
        for item in body.get("files", []):
            assets.append(
                AssetRecord(
                    asset_id=str(uuid4()),
                    external_id=item["id"],
                    name=item.get("name", ""),
                    mime_type=item.get("mimeType", "application/octet-stream"),
                    modified_time=item.get("modifiedTime", utcnow().isoformat()),
                    web_view_link=item.get("webViewLink", ""),
                )
            )

        return assets, body.get("nextPageToken")


@dataclass
class ConnectorSource:
    id: str
    provider: str
    external_account_id: str
    access_token: str
    refresh_token: str | None = None
    access_token_expires_at: datetime | None = None
    created_at: datetime = field(default_factory=utcnow)


class ConnectorService:
    def __init__(self, connector: AssetConnector, store: ConnectorStore) -> None:
        self.connector = connector
        self.store = store

    def start_oauth(self) -> tuple[str, str]:
        state = str(uuid4())
        self.store.save_oauth_state(state=state, provider=self.connector.provider)
        return state, self.connector.build_oauth_authorize_url(state)

    def complete_oauth(self, state: str, code: str) -> ConnectorSource:
        oauth_state = self.store.pop_oauth_state(state)
        if not oauth_state:
            raise ValueError("Invalid OAuth state")
        token = self.connector.exchange_code(code)
        source = ConnectorSource(
            id=str(uuid4()),
            provider=self.connector.provider,
            external_account_id=f"{self.connector.provider}_{uuid4().hex[:10]}",
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            access_token_expires_at=token.expires_at,
        )
        return self.store.create_source(source)

    def start_incremental_sync(self, source_id: str, folder_id: str, page_token: str | None = None) -> SyncJob:
        source = self.store.get_source(source_id)
        if not source:
            raise ValueError("Source not found")

        job = SyncJob(
            id=str(uuid4()),
            source_id=source_id,
            status="running",
            started_at=utcnow(),
        )
        self.store.create_sync_job(job)

        try:
            assets, next_token = self.connector.scan_folder(
                access_token=source.access_token,
                folder_id=folder_id,
                page_token=page_token,
            )
        except PermissionError:
            if not source.refresh_token:
                raise
            refreshed = self.connector.refresh_access_token(source.refresh_token)
            updated_source = self.store.update_source_tokens(
                source_id=source.id,
                access_token=refreshed.access_token,
                refresh_token=refreshed.refresh_token,
                expires_at=refreshed.expires_at,
            )
            if not updated_source:
                raise ValueError("Source not found")
            source = updated_source
            assets, next_token = self.connector.scan_folder(
                access_token=source.access_token,
                folder_id=folder_id,
                page_token=page_token,
            )

        try:
            synced_count = self.store.upsert_assets(source_id=source_id, assets=assets)
            job.synced_count = synced_count
            job.next_page_token = next_token
            job.status = "completed"
            job.ended_at = utcnow()
            return self.store.update_sync_job(job)
        except Exception as exc:  # pragma: no cover - defensive placeholder
            job.status = "failed"
            job.error_message = str(exc)
            job.ended_at = utcnow()
            return self.store.update_sync_job(job)

    def get_sync_job(self, sync_job_id: str) -> SyncJob | None:
        return self.store.get_sync_job(sync_job_id)
