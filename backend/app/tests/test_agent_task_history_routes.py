import sys
import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.routes.research_runtime import get_research_runtime_service  # noqa: E402
from app.main import create_application  # noqa: E402
from app.repositories.ledger_repository import LedgerRepository  # noqa: E402
from app.schemas.agent_tasks import AgentTaskHistoryResponse, AgentTaskStatusResponse  # noqa: E402
from app.services.research_runtime_service import ResearchRuntimeService  # noqa: E402


class AgentTaskHistoryRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        repository = LedgerRepository(self.temp_dir.name)
        self.service = ResearchRuntimeService(repository=repository, runtime_mode="mock")
        self.app = create_application()
        self.app.dependency_overrides[get_research_runtime_service] = lambda: self.service
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        self.service.shutdown(wait=True)
        self.temp_dir.cleanup()

    def _wait_for_status(self, run_id: str, statuses: set[str], *, timeout: float = 4.0) -> AgentTaskStatusResponse:
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            response = self.client.get(f"/api/agent/tasks/{run_id}")
            self.assertEqual(response.status_code, 200)
            payload = AgentTaskStatusResponse.model_validate(response.json())
            if payload.status in statuses:
                return payload
            time.sleep(0.05)
        self.fail(f"Task did not reach expected status: {run_id} -> {statuses}")

    def _create_history_fixture(self) -> None:
        tasks = [
            {
                "task_type": "competition_recommendation",
                "task_id": "run-history-001",
                "session_id": "session-history-001",
                "objective": "历史列表推荐任务",
                "payload": {
                    "profile": {
                        "direction": "algorithms",
                        "grade": "freshman",
                        "ability_tags": ["algorithms", "cpp"],
                        "preference_tags": ["team"],
                    }
                },
                "expected_statuses": {"completed"},
            },
            {
                "task_type": "competition_eligibility_check",
                "task_id": "run-history-002",
                "session_id": "session-history-002",
                "objective": "历史列表审核任务",
                "payload": {
                    "competition_id": 10,
                    "profile": {
                        "direction": "robotics",
                        "grade": "sophomore",
                        "ability_tags": ["robotics", "control", "testing"],
                        "preference_tags": ["team"],
                    },
                },
                "expected_statuses": {"awaiting_review"},
            },
            {
                "task_type": "competition_timeline_plan",
                "task_id": "run-history-003",
                "session_id": "session-history-003",
                "objective": "历史列表计划任务",
                "payload": {
                    "competition_id": 24,
                    "deadline": "2026-06-20T18:00:00+00:00",
                    "constraints": {"available_hours_per_week": 6, "team_size": 2},
                },
                "expected_statuses": {"completed"},
            },
        ]
        for item in tasks:
            response = self.client.post(
                "/api/agent/tasks",
                json={
                    "task_type": item["task_type"],
                    "task_id": item["task_id"],
                    "session_id": item["session_id"],
                    "objective": item["objective"],
                    "payload": item["payload"],
                    "dry_run": False,
                },
            )
            self.assertEqual(response.status_code, 201)
            self._wait_for_status(item["task_id"], item["expected_statuses"])
            time.sleep(0.02)

    def test_history_route_supports_filters_and_pagination(self) -> None:
        self._create_history_fixture()

        all_items = AgentTaskHistoryResponse.model_validate(
            self.client.get("/api/agent/tasks?limit=2&offset=0").json()
        )
        self.assertEqual(all_items.limit, 2)
        self.assertEqual(all_items.offset, 0)
        self.assertEqual(all_items.total, 3)
        self.assertEqual(len(all_items.items), 2)

        awaiting_review = AgentTaskHistoryResponse.model_validate(
            self.client.get("/api/agent/tasks?status=awaiting_review").json()
        )
        self.assertEqual(awaiting_review.total, 1)
        self.assertEqual(awaiting_review.items[0].run_id, "run-history-002")
        self.assertTrue(awaiting_review.items[0].awaiting_review)
        self.assertIn("review_accept", awaiting_review.items[0].available_actions)

        timeline_only = AgentTaskHistoryResponse.model_validate(
            self.client.get("/api/agent/tasks?task_type=competition_timeline_plan").json()
        )
        self.assertEqual(timeline_only.total, 1)
        self.assertEqual(timeline_only.items[0].task_type, "competition_timeline_plan")

        second_page = AgentTaskHistoryResponse.model_validate(
            self.client.get("/api/agent/tasks?limit=1&offset=1").json()
        )
        self.assertEqual(second_page.limit, 1)
        self.assertEqual(second_page.offset, 1)
        self.assertEqual(len(second_page.items), 1)


if __name__ == "__main__":
    unittest.main()
