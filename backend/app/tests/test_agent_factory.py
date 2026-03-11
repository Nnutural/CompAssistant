import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.agent_factory import ResearchAgentFactory, _extract_json_candidate_from_exception_message  # noqa: E402
from app.agents.runtime_tools import ResearchAgentContext  # noqa: E402
from app.schemas.research_runtime import AgentTaskEnvelope, ResearchLedger, ResearchScope  # noqa: E402


class AgentFactoryHelperTests(unittest.TestCase):
    def test_extract_json_candidate_skips_prefix_and_suffix_noise(self) -> None:
        message = (
            "Invalid JSON when parsing "
            '{"task_id":"eval-recommendation-001","recommendations":[{"competition_id":14}]} '
            "for TypeAdapter(CompetitionRecommendationArtifact); 2 validation errors"
        )

        candidate = _extract_json_candidate_from_exception_message(message)

        self.assertEqual(
            candidate,
            '{"task_id":"eval-recommendation-001","recommendations":[{"competition_id":14}]}',
        )

    def test_competition_recommender_uses_tighter_task_specific_budgets(self) -> None:
        factory = ResearchAgentFactory(
            model="deepseek-v3-2-251201",
            session_db_path=str(REPO_ROOT / "backend" / "data" / "test-sessions.sqlite3"),
            tracing_enabled=False,
        )

        structured = factory.get_run_budget(agent_name="competition-recommender", path_label="structured")
        plain_json = factory.get_run_budget(agent_name="competition-recommender", path_label="plain_json_fallback")

        self.assertEqual(structured.max_turns, 6)
        self.assertEqual(plain_json.max_turns, 4)
        self.assertEqual(structured.timeout_seconds, plain_json.timeout_seconds)

    def test_session_ids_include_runtime_invocation_id_to_avoid_cross_run_reuse(self) -> None:
        factory = ResearchAgentFactory(
            model="deepseek-v3-2-251201",
            session_db_path=str(REPO_ROOT / "backend" / "data" / "test-sessions.sqlite3"),
            tracing_enabled=False,
        )
        context_one = self._build_context(task_id="case-one", session_id="case-one")
        context_two = self._build_context(task_id="case-one", session_id="case-one")

        session_one = factory._get_or_create_session_id(context_one, "competition-recommender")
        session_two = factory._get_or_create_session_id(context_two, "competition-recommender")

        self.assertNotEqual(context_one.runtime_invocation_id, context_two.runtime_invocation_id)
        self.assertNotEqual(session_one, session_two)
        self.assertIn(context_one.runtime_invocation_id, session_one)
        self.assertIn(context_two.runtime_invocation_id, session_two)

    def _build_context(self, *, task_id: str, session_id: str) -> ResearchAgentContext:
        task = AgentTaskEnvelope(
            contract_version="1.0",
            task_id=task_id,
            session_id=session_id,
            task_type="competition_recommendation",
            requested_by="user",
            priority="normal",
            objective="debug recommendation",
            payload={"profile": {"direction": "algorithms", "grade": "freshman"}},
            constraints=[],
            dry_run=False,
            created_at=datetime.now(timezone.utc),
        )
        ledger = ResearchLedger(
            contract_version="1.0",
            ledger_id=f"ledger-{task_id}",
            session_id=session_id,
            topic="debug recommendation",
            research_question="debug recommendation",
            status="active",
            scope=ResearchScope(),
            task_history=[],
            source_registry=[],
            evidence_log=[],
            created_at=datetime.now(timezone.utc),
        )
        return ResearchAgentContext(
            task=task,
            ledger=ledger,
            model="deepseek-v3-2-251201",
            session_db_path=str(REPO_ROOT / "backend" / "data" / "test-sessions.sqlite3"),
            tracing_enabled=False,
            trace_group_id=session_id,
        )


if __name__ == "__main__":
    unittest.main()
