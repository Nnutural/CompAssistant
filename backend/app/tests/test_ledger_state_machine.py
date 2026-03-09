import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.repositories.ledger_repository import LedgerRepository  # noqa: E402
from app.schemas.research_runtime import AgentTaskEnvelope  # noqa: E402
from app.services.research_runtime_service import ResearchRuntimeService  # noqa: E402


class LedgerStateMachineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = LedgerRepository(self.temp_dir.name)
        self.service = ResearchRuntimeService(repository=self.repository, runtime_mode="mock")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_state_machine_records_all_main_states_and_events(self) -> None:
        task = AgentTaskEnvelope(
            contract_version="1.0",
            task_id="task-state-machine-001",
            session_id="session-state-machine-001",
            task_type="competition_recommendation",
            requested_by="user",
            objective="为网络安全方向学生推荐竞赛。",
            payload={
                "topic": "竞赛推荐",
                "profile": {
                    "direction": "网络安全",
                    "grade": "junior",
                    "ability_tags": ["security", "linux", "reverse"],
                    "preference_tags": ["flexible"],
                },
            },
            created_at=datetime(2026, 3, 9, 10, 0, tzinfo=timezone.utc),
            dry_run=False,
        )

        self.service.run_task(task)
        ledger = self.service.get_ledger("ledger-session-state-machine-001")

        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.current_state, "completed")
        self.assertIsNone(ledger.error_stage)
        self.assertTrue({"planning", "retrieving_local_context", "reasoning", "validating_output", "persisting_artifacts", "completed"}.issubset(set(ledger.completed_states)))

        entered_states = [event.state for event in ledger.events if event.status == "entered"]
        self.assertEqual(
            entered_states,
            [
                "received",
                "planning",
                "retrieving_local_context",
                "reasoning",
                "validating_output",
                "persisting_artifacts",
            ],
        )
        self.assertTrue(any(event.state == "completed" and event.status == "completed" for event in ledger.events))


if __name__ == "__main__":
    unittest.main()
