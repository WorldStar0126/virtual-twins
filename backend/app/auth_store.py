from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UserRecord:
    id: str
    email: str
    display_name: str
    password_hash: str
    role: str
    created_at: datetime


@dataclass
class RefreshTokenRecord:
    id: str
    user_id: str
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime


class AuthStore(Protocol):
    def create_user(self, email: str, display_name: str, password_hash: str, role: str = "viewer") -> UserRecord: ...
    def get_user_by_email(self, email: str) -> UserRecord | None: ...
    def get_user_by_id(self, user_id: str) -> UserRecord | None: ...
    def set_user_role(self, user_id: str, role: str) -> UserRecord | None: ...
    def store_refresh_token(
        self, user_id: str, token_hash: str, expires_at: datetime
    ) -> RefreshTokenRecord: ...
    def get_refresh_token(self, token_hash: str) -> RefreshTokenRecord | None: ...
    def revoke_refresh_token(self, token_hash: str) -> None: ...


class InMemoryAuthStore:
    def __init__(self) -> None:
        self.users_by_id: dict[str, UserRecord] = {}
        self.users_by_email: dict[str, UserRecord] = {}
        self.refresh_tokens: dict[str, RefreshTokenRecord] = {}

    def create_user(self, email: str, display_name: str, password_hash: str, role: str = "viewer") -> UserRecord:
        if email in self.users_by_email:
            raise ValueError("Email already exists")
        user = UserRecord(
            id=str(uuid4()),
            email=email,
            display_name=display_name,
            password_hash=password_hash,
            role=role,
            created_at=utcnow(),
        )
        self.users_by_id[user.id] = user
        self.users_by_email[email] = user
        return user

    def get_user_by_email(self, email: str) -> UserRecord | None:
        return self.users_by_email.get(email)

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        return self.users_by_id.get(user_id)

    def set_user_role(self, user_id: str, role: str) -> UserRecord | None:
        user = self.users_by_id.get(user_id)
        if not user:
            return None
        user.role = role
        self.users_by_id[user.id] = user
        self.users_by_email[user.email] = user
        return user

    def store_refresh_token(
        self, user_id: str, token_hash: str, expires_at: datetime
    ) -> RefreshTokenRecord:
        record = RefreshTokenRecord(
            id=str(uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
            created_at=utcnow(),
        )
        self.refresh_tokens[token_hash] = record
        return record

    def get_refresh_token(self, token_hash: str) -> RefreshTokenRecord | None:
        record = self.refresh_tokens.get(token_hash)
        if not record:
            return None
        if record.revoked_at is not None:
            return None
        if record.expires_at <= utcnow():
            return None
        return record

    def revoke_refresh_token(self, token_hash: str) -> None:
        record = self.refresh_tokens.get(token_hash)
        if not record:
            return
        record.revoked_at = utcnow()
        self.refresh_tokens[token_hash] = record


class PostgresAuthStore:
    _DEFAULT_SCOPE = "default_scope"

    def _get_role_for_user(self, session, user_id: str) -> str:  # noqa: ANN001
        from backend.app.db_models import TeamMembershipTable

        row = (
            session.query(TeamMembershipTable)
            .filter(TeamMembershipTable.user_id == user_id)
            .order_by(TeamMembershipTable.created_at.asc())
            .first()
        )
        return row.role if row else "viewer"

    def create_user(self, email: str, display_name: str, password_hash: str, role: str = "viewer") -> UserRecord:
        from backend.app.db import SessionLocal
        from backend.app.db_models import UserTable

        with SessionLocal() as session:
            existing = session.query(UserTable).filter(UserTable.email == email).one_or_none()
            if existing:
                raise ValueError("Email already exists")
            row = UserTable(
                id=str(uuid4()),
                email=email,
                display_name=display_name,
                password_hash=password_hash,
                created_at=utcnow(),
            )
            session.add(row)
            session.commit()
            self.set_user_role(row.id, role)
            return UserRecord(
                id=row.id,
                email=row.email,
                display_name=row.display_name,
                password_hash=row.password_hash,
                role=role,
                created_at=row.created_at,
            )

    def get_user_by_email(self, email: str) -> UserRecord | None:
        from backend.app.db import SessionLocal
        from backend.app.db_models import UserTable

        with SessionLocal() as session:
            row = session.query(UserTable).filter(UserTable.email == email).one_or_none()
            if not row:
                return None
            return UserRecord(
                id=row.id,
                email=row.email,
                display_name=row.display_name,
                password_hash=row.password_hash,
                role=self._get_role_for_user(session, row.id),
                created_at=row.created_at,
            )

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        from backend.app.db import SessionLocal
        from backend.app.db_models import UserTable

        with SessionLocal() as session:
            row = session.get(UserTable, user_id)
            if not row:
                return None
            return UserRecord(
                id=row.id,
                email=row.email,
                display_name=row.display_name,
                password_hash=row.password_hash,
                role=self._get_role_for_user(session, row.id),
                created_at=row.created_at,
            )

    def set_user_role(self, user_id: str, role: str) -> UserRecord | None:
        from backend.app.db import SessionLocal
        from backend.app.db_models import TeamMembershipTable, UserTable

        with SessionLocal() as session:
            user = session.get(UserTable, user_id)
            if not user:
                return None
            row = (
                session.query(TeamMembershipTable)
                .filter(TeamMembershipTable.user_id == user_id)
                .order_by(TeamMembershipTable.created_at.asc())
                .first()
            )
            if row:
                row.role = role
            else:
                row = TeamMembershipTable(
                    id=str(uuid4()),
                    scope_id=self._DEFAULT_SCOPE,
                    user_id=user_id,
                    role=role,
                    created_at=utcnow(),
                )
                session.add(row)
            session.commit()
            return UserRecord(
                id=user.id,
                email=user.email,
                display_name=user.display_name,
                password_hash=user.password_hash,
                role=role,
                created_at=user.created_at,
            )

    def store_refresh_token(
        self, user_id: str, token_hash: str, expires_at: datetime
    ) -> RefreshTokenRecord:
        from backend.app.db import SessionLocal
        from backend.app.db_models import AuthRefreshTokenTable

        with SessionLocal() as session:
            row = AuthRefreshTokenTable(
                id=str(uuid4()),
                user_id=user_id,
                scope_id=self._DEFAULT_SCOPE,
                token_hash=token_hash,
                expires_at=expires_at,
                revoked_at=None,
                created_at=utcnow(),
            )
            session.add(row)
            session.commit()
            return RefreshTokenRecord(
                id=row.id,
                user_id=row.user_id,
                token_hash=row.token_hash,
                expires_at=row.expires_at,
                revoked_at=row.revoked_at,
                created_at=row.created_at,
            )

    def get_refresh_token(self, token_hash: str) -> RefreshTokenRecord | None:
        from backend.app.db import SessionLocal
        from backend.app.db_models import AuthRefreshTokenTable

        with SessionLocal() as session:
            row = (
                session.query(AuthRefreshTokenTable)
                .filter(AuthRefreshTokenTable.token_hash == token_hash)
                .one_or_none()
            )
            if not row:
                return None
            if row.revoked_at is not None or row.expires_at <= utcnow():
                return None
            return RefreshTokenRecord(
                id=row.id,
                user_id=row.user_id,
                token_hash=row.token_hash,
                expires_at=row.expires_at,
                revoked_at=row.revoked_at,
                created_at=row.created_at,
            )

    def revoke_refresh_token(self, token_hash: str) -> None:
        from backend.app.db import SessionLocal
        from backend.app.db_models import AuthRefreshTokenTable

        with SessionLocal() as session:
            row = (
                session.query(AuthRefreshTokenTable)
                .filter(AuthRefreshTokenTable.token_hash == token_hash)
                .one_or_none()
            )
            if not row:
                return
            row.revoked_at = utcnow()
            session.commit()


def build_auth_store() -> AuthStore:
    backend = os.getenv("VT_STORAGE_BACKEND", "memory").strip().lower()
    if backend == "postgres":
        return PostgresAuthStore()
    return InMemoryAuthStore()
