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
        self.service.shutdown(wait=True)
        self.temp_dir.cleanup()

    def _wait_for_terminal_status(self, run_id: str, *, timeout: float = 3.0) -> AgentTaskStatusResponse:
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            response = self.client.get(f"/api/agent/tasks/{run_id}")
            self.assertEqual(response.status_code, 200)
            status_payload = AgentTaskStatusResponse.model_validate(response.json())
            if status_payload.status in {"completed", "failed", "awaiting_review"}:
                return status_payload
            time.sleep(0.05)
        self.fail(f"Task did not reach terminal state in time: {run_id}")

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
        self.assertEqual(created.status, "queued")
        self.assertEqual(created.current_state, "queued")
        self.assertEqual(created.requested_runtime_mode, "mock")
        self.assertEqual(created.effective_runtime_mode, "mock")
        self.assertEqual(created.effective_model, "mock")
        self.assertGreaterEqual(created.event_count, 3)
        self.assertEqual(created.artifact_count, 0)

        status_response = self.client.get(f"/api/agent/tasks/{created.run_id}")
        self.assertEqual(status_response.status_code, 200)
        status_payload = AgentTaskStatusResponse.model_validate(status_response.json())
        self.assertEqual(status_payload.ledger_id, "ledger-session-route-001")
        self.assertEqual(status_payload.requested_runtime_mode, "mock")
        self.assertEqual(status_payload.effective_runtime_mode, "mock")
        self.assertIn(status_payload.status, {"queued", "running", "completed", "awaiting_review"})

        events_response = self.client.get(f"/api/agent/tasks/{created.run_id}/events")
        self.assertEqual(events_response.status_code, 200)
        events_payload = AgentTaskEventsResponse.model_validate(events_response.json())
        self.assertEqual(events_payload.run_id, created.run_id)
        self.assertGreaterEqual(len(events_payload.items), 3)
        event_states = [item.state for item in events_payload.items]
        self.assertIn("received", event_states)
        self.assertIn("queued", event_states)

        artifacts_response = self.client.get(f"/api/agent/tasks/{created.run_id}/artifacts")
        self.assertEqual(artifacts_response.status_code, 200)
        artifacts_payload = AgentTaskArtifactsResponse.model_validate(artifacts_response.json())
        self.assertEqual(artifacts_payload.run_id, created.run_id)
        if artifacts_payload.current_state in {"completed", "failed", "awaiting_review"}:
            self.assertGreaterEqual(len(artifacts_payload.items), 1)
        else:
            self.assertEqual(len(artifacts_payload.items), 0)

        terminal_status = self._wait_for_terminal_status(created.run_id)
        self.assertEqual(terminal_status.status, "completed")
        self.assertEqual(terminal_status.current_state, "completed")
        self.assertEqual(terminal_status.result.status, "completed")
        self.assertTrue(terminal_status.result.summary)

        terminal_events = AgentTaskEventsResponse.model_validate(
            self.client.get(f"/api/agent/tasks/{created.run_id}/events").json()
        )
        terminal_states = [item.state for item in terminal_events.items]
        self.assertIn("running", terminal_states)
        self.assertIn("planning", terminal_states)
        self.assertIn("completed", terminal_states)

        terminal_artifacts = AgentTaskArtifactsResponse.model_validate(
            self.client.get(f"/api/agent/tasks/{created.run_id}/artifacts").json()
        )
        self.assertGreaterEqual(len(terminal_artifacts.items), 1)
        self.assertEqual(terminal_artifacts.items[0].artifact_type, "competition_recommendation")
        self.assertIsInstance(terminal_artifacts.items[0].payload, dict)
        self.assertEqual(terminal_artifacts.items[0].payload["task_type"], "competition_recommendation")

    def test_missing_run_returns_not_found(self) -> None:
        response = self.client.get("/api/agent/tasks/does-not-exist")
        self.assertEqual(response.status_code, 404)

    def test_duplicate_explicit_task_id_returns_conflict(self) -> None:
        payload = {
            "task_type": "competition_recommendation",
            "task_id": "run-duplicate-001",
            "session_id": "session-duplicate-001",
            "objective": "Create a task that should reject duplicate task ids.",
            "payload": {
                "profile": {
                    "direction": "algorithms",
                    "grade": "freshman",
                    "ability_tags": ["algorithms"],
                    "preference_tags": ["team"],
                }
            },
            "dry_run": False,
        }
        created = self.client.post("/api/agent/tasks", json=payload)
        self.assertEqual(created.status_code, 201)

        conflict = self.client.post("/api/agent/tasks", json=payload)
        self.assertEqual(conflict.status_code, 409)
        self.assertIn("task_id=run-duplicate-001", conflict.json()["detail"])


if __name__ == "__main__":
    unittest.main()
