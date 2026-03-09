import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.routes.research_runtime import get_research_runtime_service  # noqa: E402
from app.main import create_application  # noqa: E402
from app.repositories.ledger_repository import LedgerRepository  # noqa: E402
from app.schemas.agent_tasks import (  # noqa: E402
    AgentTaskArtifactsResponse,
    AgentTaskEventsResponse,
    AgentTaskStatusResponse,
)
from app.services.research_runtime_service import ResearchRuntimeService  # noqa: E402


class AgentTaskRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        repository = LedgerRepository(self.temp_dir.name)
        self.service = ResearchRuntimeService(repository=repository, runtime_mode="mock")
        self.app = create_application()
        self.app.dependency_overrides[get_research_runtime_service] = lambda: self.service
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        self.temp_dir.cleanup()

    def test_create_task_and_poll_status_events_artifacts(self) -> None:
        response = self.client.post(
            "/api/agent/tasks",
            json={
                "task_type": "competition_recommendation",
                "task_id": "run-route-001",
                "session_id": "session-route-001",
                "objective": "Recommend grounded competitions for a freshman algorithm student.",
                "payload": {
                    "profile": {
                        "direction": "算法/编程",
                        "grade": "freshman",
                        "ability_tags": ["algorithms", "cpp", "problem-solving"],
                        "preference_tags": ["team", "onsite"],
                    }
                },
                "dry_run": False,
            },
        )
        self.assertEqual(response.status_code, 201)
        created = AgentTaskStatusResponse.model_validate(response.json())
        self.assertEqual(created.run_id, "run-route-001")
        self.assertEqual(created.task_id, "run-route-001")
        self.assertEqual(created.status, "completed")
        self.assertEqual(created.current_state, "completed")
        self.assertGreaterEqual(created.event_count, 6)
        self.assertGreaterEqual(created.artifact_count, 1)

        status_response = self.client.get(f"/api/agent/tasks/{created.run_id}")
        self.assertEqual(status_response.status_code, 200)
        status_payload = AgentTaskStatusResponse.model_validate(status_response.json())
        self.assertEqual(status_payload.ledger_id, "ledger-session-route-001")
        self.assertEqual(status_payload.result.status, "completed")
        self.assertTrue(status_payload.result.summary)

        events_response = self.client.get(f"/api/agent/tasks/{created.run_id}/events")
        self.assertEqual(events_response.status_code, 200)
        events_payload = AgentTaskEventsResponse.model_validate(events_response.json())
        self.assertEqual(events_payload.run_id, created.run_id)
        self.assertGreaterEqual(len(events_payload.items), 6)
        event_states = [item.state for item in events_payload.items]
        self.assertIn("received", event_states)
        self.assertIn("planning", event_states)
        self.assertIn("completed", event_states)

        artifacts_response = self.client.get(f"/api/agent/tasks/{created.run_id}/artifacts")
        self.assertEqual(artifacts_response.status_code, 200)
        artifacts_payload = AgentTaskArtifactsResponse.model_validate(artifacts_response.json())
        self.assertEqual(artifacts_payload.run_id, created.run_id)
        self.assertGreaterEqual(len(artifacts_payload.items), 1)
        self.assertEqual(artifacts_payload.items[0].artifact_type, "competition_recommendation")
        self.assertIsInstance(artifacts_payload.items[0].payload, dict)
        self.assertEqual(artifacts_payload.items[0].payload["task_type"], "competition_recommendation")

    def test_missing_run_returns_not_found(self) -> None:
        response = self.client.get("/api/agent/tasks/does-not-exist")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
