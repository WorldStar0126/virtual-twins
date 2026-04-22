from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4

import jwt


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


Role = Literal["owner", "admin", "operator", "viewer"]


@dataclass
class AccessClaims:
    user_id: str
    role: Role
    exp: int


class AuthService:
    def __init__(self) -> None:
        self.jwt_secret = os.getenv("VT_AUTH_JWT_SECRET", "dev-insecure-secret-change-me")
        self.jwt_alg = "HS256"
        self.access_ttl_minutes = int(os.getenv("VT_AUTH_ACCESS_TTL_MINUTES", "30"))
        self.refresh_ttl_days = int(os.getenv("VT_AUTH_REFRESH_TTL_DAYS", "14"))

    def hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
        return f"scrypt${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            algo, salt_b64, digest_b64 = password_hash.split("$", 2)
            if algo != "scrypt":
                return False
            salt = base64.b64decode(salt_b64.encode())
            expected = base64.b64decode(digest_b64.encode())
            computed = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
            return hmac.compare_digest(computed, expected)
        except Exception:
            return False

    def issue_access_token(self, user_id: str, role: Role) -> tuple[str, datetime]:
        expires = utcnow() + timedelta(minutes=self.access_ttl_minutes)
        payload = {
            "sub": user_id,
            "role": role,
            "type": "access",
            "exp": int(expires.timestamp()),
            "iat": int(utcnow().timestamp()),
            "jti": str(uuid4()),
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_alg)
        return token, expires

    def issue_refresh_token(self) -> tuple[str, str, datetime]:
        raw = secrets.token_urlsafe(48)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        expires = utcnow() + timedelta(days=self.refresh_ttl_days)
        return raw, digest, expires

    def parse_access_token(self, token: str) -> AccessClaims:
        payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_alg])
        if payload.get("type") != "access":
            raise ValueError("Invalid token type")
        return AccessClaims(
            user_id=payload["sub"],
            role=payload["role"],
            exp=payload["exp"],
        )
