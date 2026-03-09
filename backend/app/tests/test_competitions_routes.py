import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import create_application  # noqa: E402


class CompetitionRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_application())

    def test_competitions_routes_still_work(self) -> None:
        list_response = self.client.get("/api/competitions")
        self.assertEqual(list_response.status_code, 200)
        competitions = list_response.json()
        self.assertGreater(len(competitions), 0)

        detail_response = self.client.get("/api/competitions/1")
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()
        self.assertEqual(detail["id"], 1)
        self.assertIn("name", detail)


if __name__ == "__main__":
    unittest.main()
