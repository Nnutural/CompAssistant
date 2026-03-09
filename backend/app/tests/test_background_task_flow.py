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
from app.schemas.agent_tasks import AgentTaskCreateRequest  # noqa: E402
from app.services.research_runtime_service import ResearchRuntimeService  # noqa: E402


class _SlowSuccessManager:
    def __init__(self, delegate):
        self.delegate = delegate

    def run(self, task, ledger, checkpoint_callback=None, abort_if_requested=None):
        time.sleep(0.35)
        return self.delegate.run(
            task,
            ledger,
            checkpoint_callback=checkpoint_callback,
            abort_if_requested=abort_if_requested,
        )


class _FailingManager:
    def run(self, task, ledger, checkpoint_callback=None, abort_if_requested=None):
        time.sleep(0.05)
        raise RuntimeError("Simulated background failure")


class BackgroundTaskFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _build_service(self, *, manager=None) -> ResearchRuntimeService:
        repository = LedgerRepository(self.temp_dir.name)
        service = ResearchRuntimeService(repository=repository, runtime_mode="mock")
        if manager is not None:
            service.manager = manager
        return service

    def _wait_for_terminal(self, service: ResearchRuntimeService, run_id: str, *, timeout: float = 4.0):
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            status = service.get_task_status(run_id)
            if status is not None and status.status in {"completed", "cancelled", "failed", "awaiting_review"}:
                return status
            time.sleep(0.05)
        self.fail(f"Run did not reach terminal state: {run_id}")

    def test_create_route_returns_before_slow_background_execution_finishes(self) -> None:
        base_service = self._build_service()
        service = self._build_service(manager=_SlowSuccessManager(base_service.manager))
        app = create_application()
        app.dependency_overrides[get_research_runtime_service] = lambda: service
        client = TestClient(app)

        started_at = time.perf_counter()
        response = client.post(
            "/api/agent/tasks",
            json={
                "task_type": "competition_recommendation",
                "task_id": "run-slow-001",
                "session_id": "session-slow-001",
                "objective": "Recommend competitions for a slow background run.",
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
        elapsed = time.perf_counter() - started_at

        self.assertEqual(response.status_code, 201)
        self.assertLess(elapsed, 0.25)
        payload = response.json()
        self.assertEqual(payload["status"], "queued")
        self.assertEqual(payload["current_state"], "queued")

        terminal = self._wait_for_terminal(service, "run-slow-001")
        self.assertEqual(terminal.status, "completed")

        app.dependency_overrides.clear()
        service.shutdown(wait=True)
        base_service.shutdown(wait=True)

    def test_background_execution_can_reach_failed_state(self) -> None:
        service = self._build_service(manager=_FailingManager())
        try:
            created = service.create_agent_task(
                AgentTaskCreateRequest.model_validate(
                    {
                        "task_type": "competition_recommendation",
                        "task_id": "run-failed-001",
                        "session_id": "session-failed-001",
                        "objective": "Force a background failure.",
                        "payload": {"profile": {"direction": "algorithms"}},
                        "dry_run": False,
                    }
                )
            )

            self.assertEqual(created.status, "queued")
            terminal = self._wait_for_terminal(service, "run-failed-001")
            self.assertEqual(terminal.status, "failed")
            self.assertEqual(terminal.current_state, "failed")
            self.assertTrue(terminal.result.blockers)
        finally:
            service.shutdown(wait=True)

    def test_background_execution_can_reach_awaiting_review_state(self) -> None:
        service = self._build_service()
        try:
            created = service.create_agent_task(
                AgentTaskCreateRequest.model_validate(
                    {
                        "task_type": "competition_eligibility_check",
                        "task_id": "run-review-001",
                        "session_id": "session-review-001",
                        "objective": "Trigger a review-required eligibility result.",
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
                    }
                )
            )

            self.assertEqual(created.status, "queued")
            terminal = self._wait_for_terminal(service, "run-review-001")
            self.assertEqual(terminal.status, "awaiting_review")
            self.assertEqual(terminal.current_state, "awaiting_review")
            self.assertEqual(terminal.result.status, "needs_human")
        finally:
            service.shutdown(wait=True)


if __name__ == "__main__":
    unittest.main()
