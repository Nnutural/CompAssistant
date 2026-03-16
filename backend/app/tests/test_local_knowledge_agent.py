import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.eligibility_checker import EligibilityCheckerAgent  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.crawler.schemas import KnowledgeRecord  # noqa: E402
from app.retrieval.sqlite_index_store import SQLiteIndexStore  # noqa: E402
from app.schemas.research_runtime import AgentTaskEnvelope, ResearchLedger, ResearchScope  # noqa: E402
from app.tools import load_competition_by_id, unwrap_tool_result  # noqa: E402


class LocalKnowledgeAgentTests(unittest.TestCase):
    def test_eligibility_agent_uses_local_retrieval_when_enabled(self) -> None:
        competition = unwrap_tool_result(load_competition_by_id(1), "load_competition_by_id")
        previous_enabled = settings.experimental_local_knowledge_enabled
        previous_db = settings.experimental_local_knowledge_index_db
        previous_top_k = settings.experimental_local_knowledge_top_k

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "knowledge.sqlite3"
            store = SQLiteIndexStore(db_path=db_path)
            store.upsert(
                KnowledgeRecord(
                    record_id="knowledge-policy-competition-001",
                    doc_id="policy-competition-001",
                    title=f"{competition['name']} policy note",
                    summary="Local registration policy summary for the target competition.",
                    content_text=f"{competition['name']} registration policy eligibility rules and organizer guidance.",
                    source_type="policy",
                    source_name="gov-policy-demo",
                    tags=["policy", "competition"],
                    publish_time=datetime.now(timezone.utc),
                    url="https://example.com/policy",
                    searchable_text=f"{competition['name']} registration policy eligibility rules organizer guidance.",
                    indexed_at=datetime.now(timezone.utc),
                )
            )

            settings.experimental_local_knowledge_enabled = True
            settings.experimental_local_knowledge_index_db = str(db_path)
            settings.experimental_local_knowledge_top_k = 2
            try:
                task = AgentTaskEnvelope(
                    contract_version="1.0",
                    task_id="run-eligibility-local-001",
                    session_id="session-eligibility-local-001",
                    task_type="competition_eligibility_check",
                    requested_by="user",
                    priority="normal",
                    objective="Check local eligibility grounding.",
                    payload={
                        "competition_id": 1,
                        "profile": {
                            "grade": "junior",
                            "direction": competition.get("field"),
                            "ability_tags": ["innovation", "presentation"],
                        },
                    },
                    constraints=[],
                    dry_run=False,
                    created_at=datetime.now(timezone.utc),
                )
                ledger = ResearchLedger(
                    contract_version="1.0",
                    ledger_id="ledger-session-eligibility-local-001",
                    session_id=task.session_id,
                    topic="competition_eligibility_check",
                    research_question=task.objective,
                    status="active",
                    scope=ResearchScope(),
                    task_history=[],
                    source_registry=[],
                    evidence_log=[],
                    created_at=datetime.now(timezone.utc),
                )

                output = EligibilityCheckerAgent().run(task, ledger)
            finally:
                settings.experimental_local_knowledge_enabled = previous_enabled
                settings.experimental_local_knowledge_index_db = previous_db
                settings.experimental_local_knowledge_top_k = previous_top_k

        self.assertTrue(
            any("Grounded with local document" in item for item in output["rationale"]),
            output["rationale"],
        )
        self.assertTrue(
            any("Local knowledge reference" in item for item in output["attention_points"]),
            output["attention_points"],
        )


if __name__ == "__main__":
    unittest.main()
