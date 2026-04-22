from __future__ import annotations

import unittest
from uuid import uuid4

try:
    from fastapi.testclient import TestClient
    from backend.app.main import app
except ModuleNotFoundError:  # pragma: no cover - environment guard
    TestClient = None
    app = None


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if TestClient is None or app is None:
            raise unittest.SkipTest("fastapi dependency is not available in this environment")
        cls.client = TestClient(app)

    def _auth_headers_for_new_user(self) -> dict:
        suffix = uuid4().hex[:8]
        signup = self.client.post(
            "/v1/auth/signup",
            json={
                "email": f"contract-{suffix}@example.com",
                "password": "ContractPass123!",
                "display_name": "Contract User",
            },
        )
        self.assertEqual(signup.status_code, 201)
        token = signup.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_error_envelope_for_missing_job(self) -> None:
        headers = self._auth_headers_for_new_user()
        response = self.client.get(f"/v1/jobs/{uuid4()}/events", headers=headers)
        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertIn("error", body)
        self.assertEqual(body["error"]["code"], "http_404")
        self.assertIn("message", body["error"])

    def test_create_job_idempotency_replay(self) -> None:
        headers = self._auth_headers_for_new_user()
        payload = {
            "client_slug": "client-contract",
            "format_seconds": 20,
            "idempotency_key": f"idem-{uuid4()}",
        }
        first = self.client.post("/v1/jobs", json=payload, headers=headers)
        self.assertEqual(first.status_code, 201)
        first_body = first.json()
        self.assertFalse(first_body["idempotency_replayed"])

        second = self.client.post("/v1/jobs", json=payload, headers=headers)
        self.assertEqual(second.status_code, 200)
        second_body = second.json()
        self.assertTrue(second_body["idempotency_replayed"])
        self.assertEqual(second_body["id"], first_body["id"])


if __name__ == "__main__":
    unittest.main()
