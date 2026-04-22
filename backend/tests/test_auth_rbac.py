from __future__ import annotations

import unittest
from uuid import uuid4

try:
    from fastapi.testclient import TestClient

    from backend.app.main import app, auth_service, auth_store
except ModuleNotFoundError:  # pragma: no cover - environment guard
    TestClient = None
    app = None
    auth_service = None
    auth_store = None


class AuthRbacTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if TestClient is None or app is None:
            raise unittest.SkipTest("fastapi dependency is not available in this environment")
        cls.client = TestClient(app)

    def test_jobs_endpoint_requires_auth(self) -> None:
        response = self.client.post(
            "/v1/jobs",
            json={"client_slug": "c1", "format_seconds": 20},
        )
        self.assertEqual(response.status_code, 401)

    def test_signup_and_owner_can_create_job(self) -> None:
        suffix = uuid4().hex[:8]
        signup = self.client.post(
            "/v1/auth/signup",
            json={
                "email": f"owner-{suffix}@example.com",
                "password": "StrongPass123!",
                "display_name": "Owner User",
            },
        )
        self.assertEqual(signup.status_code, 201)
        body = signup.json()
        token = body["access_token"]

        create = self.client.post(
            "/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={"client_slug": "c1", "format_seconds": 20},
        )
        self.assertEqual(create.status_code, 201)

    def test_non_demo_login_is_rejected(self) -> None:
        suffix = uuid4().hex[:8]
        signup = self.client.post(
            "/v1/auth/signup",
            json={
                "email": f"owner2-{suffix}@example.com",
                "password": "StrongPass123!",
                "display_name": "Owner Two",
            },
        )
        self.assertEqual(signup.status_code, 201)

        viewer_email = f"viewer-{suffix}@example.com"
        viewer_password = "ViewerPass123!"
        user = auth_store.create_user(  # type: ignore[union-attr]
            email=viewer_email,
            display_name="Viewer User",
            password_hash=auth_service.hash_password(viewer_password),  # type: ignore[union-attr]
        )
        auth_store.set_user_role(user_id=user.id, role="viewer")  # type: ignore[union-attr]

        login = self.client.post(
            "/v1/auth/login",
            json={"email": viewer_email, "password": viewer_password},
        )
        self.assertEqual(login.status_code, 401)


if __name__ == "__main__":
    unittest.main()
