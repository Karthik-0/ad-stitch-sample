import unittest

from fastapi.testclient import TestClient

from main import app


class EndpointsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "ssai-poc")

    def test_create_session_response_shape(self) -> None:
        response = self.client.post("/session/new", json={"content_id": "demo", "preroll": True})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("session_id", payload)
        self.assertIn("master_url", payload)
        self.assertTrue(payload["session_id"])
        self.assertTrue(payload["master_url"].startswith("http://testserver/session/"))
        self.assertTrue(payload["master_url"].endswith("/master.m3u8"))

    def test_create_session_returns_unique_ids(self) -> None:
        response_a = self.client.post("/session/new", json={"content_id": "demo", "preroll": True})
        response_b = self.client.post("/session/new", json={"content_id": "demo", "preroll": True})
        sid_a = response_a.json()["session_id"]
        sid_b = response_b.json()["session_id"]
        self.assertNotEqual(sid_a, sid_b)


if __name__ == "__main__":
    unittest.main()
