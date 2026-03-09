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
from app.schemas.agent_tasks import AgentTaskStatusResponse  # noqa: E402
from app.services.research_runtime_service import ResearchRuntimeService  # noqa: E402


class _CancellableSlowManager:
    def __init__(self, delegate):
        self.delegate = delegate

    def run(self, task, ledger, checkpoint_callback=None, abort_if_requested=None):
        for _ in range(8):
            time.sleep(0.04)
            if abort_if_requested is not None:
                abort_if_requested(ledger)
        return self.delegate.run(
            task,
            ledger,
            checkpoint_callback=checkpoint_callback,
            abort_if_requested=abort_if_requested,
        )


class AgentTaskControlRouteTests(unittest.TestCase):
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

    def test_cancel_route_marks_running_task_cancelled(self) -> None:
        self.service.manager = _CancellableSlowManager(self.service.manager)
        created = self.client.post(
            "/api/agent/tasks",
            json={
                "task_type": "competition_recommendation",
                "task_id": "run-cancel-001",
                "session_id": "session-cancel-001",
                "objective": "Create a task that will be cancelled.",
                "payload": {
                    "profile": {
                        "direction": "algorithms",
                        "grade": "freshman",
                        "ability_tags": ["algorithms", "cpp"],
                        "preference_tags": ["team"],
                    }
                },
                "dry_run": False,
            },
        )
        self.assertEqual(created.status_code, 201)
        self._wait_for_status("run-cancel-001", {"running"})

        cancelled = self.client.post(
            "/api/agent/tasks/run-cancel-001/cancel",
            json={"note": "操作员取消当前任务"},
        )
        self.assertEqual(cancelled.status_code, 200)
        payload = cancelled.json()
        self.assertEqual(payload["action"], "cancel")
        self.assertEqual(payload["task"]["status"], "cancelled")
        self.assertEqual(payload["task"]["current_state"], "cancelled")

        terminal = self._wait_for_status("run-cancel-001", {"cancelled"})
        self.assertEqual(terminal.result.status, "blocked")

        events = self.client.get("/api/agent/tasks/run-cancel-001/events").json()["items"]
        self.assertTrue(any(item["state"] == "cancelled" for item in events))

    def test_retry_route_creates_new_run_with_parent_link(self) -> None:
        created = self.client.post(
            "/api/agent/tasks",
            json={
                "task_type": "competition_eligibility_check",
                "task_id": "run-retry-source-001",
                "session_id": "session-retry-source-001",
                "objective": "Create a review-required task for retry.",
                "payload": {
                    "competition_id": 10,
                    "profile": {
                        "direction": "robotics",
                        "grade": "sophomore",
                        "ability_tags": ["robotics", "control", "testing"],
                        "preference_tags": ["team"],
                    },
                },
                "dry_run": False,
            },
        )
        self.assertEqual(created.status_code, 201)
        source_status = self._wait_for_status("run-retry-source-001", {"awaiting_review"})
        self.assertEqual(source_status.status, "awaiting_review")

        retried = self.client.post("/api/agent/tasks/run-retry-source-001/retry")
        self.assertEqual(retried.status_code, 200)
        payload = retried.json()
        self.assertEqual(payload["action"], "retry")
        self.assertEqual(payload["source_run_id"], "run-retry-source-001")
        self.assertNotEqual(payload["new_run"]["run_id"], "run-retry-source-001")
        self.assertEqual(payload["new_run"]["status"], "queued")

        new_run_id = payload["new_run"]["run_id"]
        new_ledger = self.service.repository.find_by_run_id(new_run_id)
        self.assertIsNotNone(new_ledger)
        self.assertEqual(new_ledger.parent_run_id, "run-retry-source-001")

        source_ledger = self.service.repository.find_by_run_id("run-retry-source-001")
        self.assertIsNotNone(source_ledger)
        self.assertTrue(any(record.action == "retry" for record in source_ledger.control_records))

    def test_review_route_supports_annotate_accept_and_reject(self) -> None:
        created = self.client.post(
            "/api/agent/tasks",
            json={
                "task_type": "competition_eligibility_check",
                "task_id": "run-review-control-001",
                "session_id": "session-review-control-001",
                "objective": "Create a review-required task for manual control.",
                "payload": {
                    "competition_id": 10,
                    "profile": {
                        "direction": "robotics",
                        "grade": "sophomore",
                        "ability_tags": ["robotics", "control", "testing"],
                        "preference_tags": ["team"],
                    },
                },
                "dry_run": False,
            },
        )
        self.assertEqual(created.status_code, 201)
        self._wait_for_status("run-review-control-001", {"awaiting_review"})

        annotate = self.client.post(
            "/api/agent/tasks/run-review-control-001/review",
            json={"decision": "annotate", "note": "需要导师进一步确认"},
        )
        self.assertEqual(annotate.status_code, 200)
        self.assertEqual(annotate.json()["task"]["status"], "awaiting_review")

        accept = self.client.post(
            "/api/agent/tasks/run-review-control-001/review",
            json={"decision": "accept", "note": "人工审核通过"},
        )
        self.assertEqual(accept.status_code, 200)
        self.assertEqual(accept.json()["task"]["status"], "completed")

        reject_source = self.client.post(
            "/api/agent/tasks",
            json={
                "task_type": "competition_eligibility_check",
                "task_id": "run-review-reject-001",
                "session_id": "session-review-reject-001",
                "objective": "Create another review-required task.",
                "payload": {
                    "competition_id": 10,
                    "profile": {
                        "direction": "robotics",
                        "grade": "sophomore",
                        "ability_tags": ["robotics", "control", "testing"],
                        "preference_tags": ["team"],
                    },
                },
                "dry_run": False,
            },
        )
        self.assertEqual(reject_source.status_code, 201)
        self._wait_for_status("run-review-reject-001", {"awaiting_review"})

        reject = self.client.post(
            "/api/agent/tasks/run-review-reject-001/review",
            json={"decision": "reject", "note": "人工审核驳回"},
        )
        self.assertEqual(reject.status_code, 200)
        self.assertEqual(reject.json()["task"]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
