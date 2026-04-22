from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from backend.app.connectors import AssetRecord, ConnectorSource, SyncJob


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConnectorStore(Protocol):
    def save_oauth_state(self, state: str, provider: str) -> None: ...
    def pop_oauth_state(self, state: str) -> str | None: ...
    def create_source(self, source: ConnectorSource) -> ConnectorSource: ...
    def update_source_tokens(
        self, source_id: str, access_token: str, refresh_token: str | None, expires_at: datetime | None
    ) -> ConnectorSource | None: ...
    def get_source(self, source_id: str) -> ConnectorSource | None: ...
    def create_sync_job(self, sync_job: SyncJob) -> SyncJob: ...
    def update_sync_job(self, sync_job: SyncJob) -> SyncJob: ...
    def get_sync_job(self, sync_job_id: str) -> SyncJob | None: ...
    def upsert_assets(self, source_id: str, assets: list[AssetRecord]) -> int: ...


class InMemoryConnectorStore:
    def __init__(self) -> None:
        self._oauth_states: dict[str, str] = {}
        self._sources: dict[str, ConnectorSource] = {}
        self._sync_jobs: dict[str, SyncJob] = {}
        self._assets_by_source: dict[str, dict[str, AssetRecord]] = {}

    def save_oauth_state(self, state: str, provider: str) -> None:
        self._oauth_states[state] = provider

    def pop_oauth_state(self, state: str) -> str | None:
        return self._oauth_states.pop(state, None)

    def create_source(self, source: ConnectorSource) -> ConnectorSource:
        self._sources[source.id] = source
        return source

    def update_source_tokens(
        self, source_id: str, access_token: str, refresh_token: str | None, expires_at: datetime | None
    ) -> ConnectorSource | None:
        source = self._sources.get(source_id)
        if not source:
            return None
        source.access_token = access_token
        source.refresh_token = refresh_token
        source.access_token_expires_at = expires_at
        self._sources[source_id] = source
        return source

    def get_source(self, source_id: str) -> ConnectorSource | None:
        return self._sources.get(source_id)

    def create_sync_job(self, sync_job: SyncJob) -> SyncJob:
        self._sync_jobs[sync_job.id] = sync_job
        return sync_job

    def update_sync_job(self, sync_job: SyncJob) -> SyncJob:
        self._sync_jobs[sync_job.id] = sync_job
        return sync_job

    def get_sync_job(self, sync_job_id: str) -> SyncJob | None:
        return self._sync_jobs.get(sync_job_id)

    def upsert_assets(self, source_id: str, assets: list[AssetRecord]) -> int:
        if source_id not in self._assets_by_source:
            self._assets_by_source[source_id] = {}
        merged = self._assets_by_source[source_id]
        for asset in assets:
            merged[asset.external_id] = asset
        return len(assets)


class PostgresConnectorStore:
    _DEFAULT_SCOPE = "default_scope"

    def save_oauth_state(self, state: str, provider: str) -> None:
        from backend.app.db import SessionLocal
        from backend.app.db_models import ConnectorOAuthStateTable

        with SessionLocal() as session:
            row = ConnectorOAuthStateTable(state=state, scope_id=self._DEFAULT_SCOPE, provider=provider)
            session.merge(row)
            session.commit()

    def pop_oauth_state(self, state: str) -> str | None:
        from backend.app.db import SessionLocal
        from backend.app.db_models import ConnectorOAuthStateTable

        with SessionLocal() as session:
            row = session.get(ConnectorOAuthStateTable, state)
            if not row:
                return None
            result = row.provider
            session.delete(row)
            session.commit()
            return result

    def create_source(self, source: ConnectorSource) -> ConnectorSource:
        from backend.app.db import SessionLocal
        from backend.app.db_models import AssetSourceTable

        with SessionLocal() as session:
            row = AssetSourceTable(
                id=source.id,
                scope_id=self._DEFAULT_SCOPE,
                provider=source.provider,
                external_account_id=source.external_account_id,
                access_token=source.access_token,
                refresh_token=source.refresh_token,
                access_token_expires_at=source.access_token_expires_at,
                created_at=source.created_at,
            )
            session.add(row)
            session.commit()
            return source

    def update_source_tokens(
        self, source_id: str, access_token: str, refresh_token: str | None, expires_at: datetime | None
    ) -> ConnectorSource | None:
        from backend.app.db import SessionLocal
        from backend.app.db_models import AssetSourceTable

        with SessionLocal() as session:
            row = session.get(AssetSourceTable, source_id)
            if not row:
                return None
            row.access_token = access_token
            row.refresh_token = refresh_token
            row.access_token_expires_at = expires_at
            session.commit()
            return ConnectorSource(
                id=row.id,
                provider=row.provider,
                external_account_id=row.external_account_id,
                access_token=row.access_token,
                refresh_token=row.refresh_token,
                access_token_expires_at=row.access_token_expires_at,
                created_at=row.created_at,
            )

    def get_source(self, source_id: str) -> ConnectorSource | None:
        from backend.app.db import SessionLocal
        from backend.app.db_models import AssetSourceTable

        with SessionLocal() as session:
            row = session.get(AssetSourceTable, source_id)
            if not row:
                return None
            return ConnectorSource(
                id=row.id,
                provider=row.provider,
                external_account_id=row.external_account_id,
                access_token=row.access_token,
                refresh_token=row.refresh_token,
                access_token_expires_at=row.access_token_expires_at,
                created_at=row.created_at,
            )

    def create_sync_job(self, sync_job: SyncJob) -> SyncJob:
        from backend.app.db import SessionLocal
        from backend.app.db_models import AssetSyncJobTable

        with SessionLocal() as session:
            row = AssetSyncJobTable(
                id=sync_job.id,
                scope_id=self._DEFAULT_SCOPE,
                source_id=sync_job.source_id,
                status=sync_job.status,
                synced_count=sync_job.synced_count,
                next_page_token=sync_job.next_page_token,
                error_message=sync_job.error_message,
                started_at=sync_job.started_at,
                ended_at=sync_job.ended_at,
            )
            session.add(row)
            session.commit()
            return sync_job

    def update_sync_job(self, sync_job: SyncJob) -> SyncJob:
        from backend.app.db import SessionLocal
        from backend.app.db_models import AssetSyncJobTable

        with SessionLocal() as session:
            row = session.get(AssetSyncJobTable, sync_job.id)
            if not row:
                return sync_job
            row.status = sync_job.status
            row.synced_count = sync_job.synced_count
            row.next_page_token = sync_job.next_page_token
            row.error_message = sync_job.error_message
            row.started_at = sync_job.started_at
            row.ended_at = sync_job.ended_at
            session.commit()
            return sync_job

    def get_sync_job(self, sync_job_id: str) -> SyncJob | None:
        from backend.app.db import SessionLocal
        from backend.app.db_models import AssetSyncJobTable

        with SessionLocal() as session:
            row = session.get(AssetSyncJobTable, sync_job_id)
            if not row:
                return None
            return SyncJob(
                id=row.id,
                source_id=row.source_id,
                status=row.status,
                started_at=row.started_at,
                ended_at=row.ended_at,
                synced_count=row.synced_count,
                next_page_token=row.next_page_token,
                error_message=row.error_message,
            )

    def upsert_assets(self, source_id: str, assets: list[AssetRecord]) -> int:
        from sqlalchemy import select

        from backend.app.db import SessionLocal
        from backend.app.db_models import ConnectorAssetTable

        with SessionLocal() as session:
            for asset in assets:
                existing = session.execute(
                    select(ConnectorAssetTable).where(
                        ConnectorAssetTable.source_id == source_id,
                        ConnectorAssetTable.external_id == asset.external_id,
                    )
                ).scalar_one_or_none()
                if existing:
                    existing.name = asset.name
                    existing.mime_type = asset.mime_type
                    existing.modified_time = asset.modified_time
                    existing.web_view_link = asset.web_view_link
                    existing.updated_at = utcnow()
                else:
                    row = ConnectorAssetTable(
                        id=asset.asset_id,
                        source_id=source_id,
                        scope_id=self._DEFAULT_SCOPE,
                        external_id=asset.external_id,
                        name=asset.name,
                        mime_type=asset.mime_type,
                        modified_time=asset.modified_time,
                        web_view_link=asset.web_view_link,
                        created_at=utcnow(),
                        updated_at=utcnow(),
                    )
                    session.add(row)
            session.commit()
        return len(assets)


def build_connector_store() -> ConnectorStore:
    backend = os.getenv("VT_STORAGE_BACKEND", "memory").strip().lower()
    if backend == "postgres":
        return PostgresConnectorStore()
    return InMemoryConnectorStore()
