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


class AgentTaskFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = LedgerRepository(self.temp_dir.name)
        self.service = ResearchRuntimeService(repository=self.repository, runtime_mode="mock")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _build_task(self, *, task_id: str, session_id: str, task_type: str, objective: str, payload: dict) -> AgentTaskEnvelope:
        return AgentTaskEnvelope(
            contract_version="1.0",
            task_id=task_id,
            session_id=session_id,
            task_type=task_type,
            requested_by="user",
            objective=objective,
            payload=payload,
            created_at=datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc),
            dry_run=False,
        )

    def test_competition_recommendation_flow_returns_structured_artifact(self) -> None:
        task = self._build_task(
            task_id="task-recommendation-001",
            session_id="session-recommendation-001",
            task_type="competition_recommendation",
            objective="为算法方向大一学生推荐合适的竞赛。",
            payload={
                "topic": "竞赛推荐",
                "profile": {
                    "direction": "算法/编程",
                    "grade": "freshman",
                    "ability_tags": ["algorithms", "cpp", "problem-solving"],
                    "preference_tags": ["team", "onsite"],
                },
            },
        )

        result = self.service.run_task(task)
        ledger = self.service.get_ledger("ledger-session-recommendation-001")

        self.assertEqual(result.status, "completed")
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.current_state, "completed")
        self.assertEqual(ledger.repaired_outputs["final"]["task_type"], "competition_recommendation")
        self.assertGreaterEqual(len(ledger.repaired_outputs["final"]["recommendations"]), 3)
        self.assertGreaterEqual(len(ledger.artifacts), 1)

    def test_competition_eligibility_flow_returns_clear_decision(self) -> None:
        task = self._build_task(
            task_id="task-eligibility-001",
            session_id="session-eligibility-001",
            task_type="competition_eligibility_check",
            objective="判断该学生画像是否适合参加蓝桥杯。",
            payload={
                "topic": "竞赛资格判断",
                "competition_id": 14,
                "profile": {
                    "direction": "算法/编程",
                    "grade": "freshman",
                    "ability_tags": ["algorithms", "python", "problem-solving"],
                    "preference_tags": ["team"],
                },
            },
        )

        result = self.service.run_task(task)
        ledger = self.service.get_ledger("ledger-session-eligibility-001")

        self.assertEqual(result.status, "completed")
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.repaired_outputs["final"]["task_type"], "competition_eligibility_check")
        self.assertEqual(ledger.repaired_outputs["final"]["competition_id"], 14)
        self.assertIn(ledger.repaired_outputs["final"]["eligibility_label"], {"recommended", "borderline"})

    def test_competition_timeline_flow_returns_reverse_schedule(self) -> None:
        task = self._build_task(
            task_id="task-timeline-001",
            session_id="session-timeline-001",
            task_type="competition_timeline_plan",
            objective="为软件杯生成倒排计划。",
            payload={
                "topic": "竞赛倒排计划",
                "competition_id": 24,
                "deadline": "2026-06-20T18:00:00+00:00",
                "constraints": {
                    "available_hours_per_week": 5,
                    "team_size": 2,
                },
            },
        )

        result = self.service.run_task(task)
        ledger = self.service.get_ledger("ledger-session-timeline-001")

        self.assertEqual(result.status, "completed")
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.repaired_outputs["final"]["task_type"], "competition_timeline_plan")
        self.assertGreaterEqual(len(ledger.repaired_outputs["final"]["milestones"]), 3)
        self.assertGreaterEqual(len(ledger.repaired_outputs["final"]["reverse_schedule"]), 3)


if __name__ == "__main__":
    unittest.main()
