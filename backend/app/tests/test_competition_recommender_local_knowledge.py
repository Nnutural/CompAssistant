import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.competition_recommender import CompetitionRecommenderAgent  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.crawler.schemas import KnowledgeRecord  # noqa: E402
from app.retrieval.sqlite_index_store import SQLiteIndexStore  # noqa: E402
from app.schemas.research_runtime import AgentTaskEnvelope, ResearchLedger, ResearchScope  # noqa: E402


class CompetitionRecommenderLocalKnowledgeTests(unittest.TestCase):
    def test_competition_recommender_uses_local_retrieval_when_enabled(self) -> None:
        previous_enabled = settings.experimental_local_knowledge_enabled
        previous_db = settings.experimental_local_knowledge_index_db
        previous_top_k = settings.experimental_local_knowledge_top_k

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "knowledge.sqlite3"
            store = SQLiteIndexStore(db_path=db_path)
            store.upsert(
                KnowledgeRecord(
                    record_id="knowledge-template-competition-001",
                    doc_id="template-competition-001",
                    title="创新竞赛立项模板",
                    summary="适合创新创业方向学生的项目书模板。",
                    content_text="创新竞赛项目书模板，强调问题定义、团队分工、原型验证和路演叙事。 Innovation competition template for student teams.",
                    source_type="excellent_template",
                    source_channel="local_file",
                    source_name="excellent_template_curated",
                    implementation_status="importer",
                    tags=["excellent_template", "innovation", "competition"],
                    publish_time=datetime.now(timezone.utc),
                    url="local://template-competition-001",
                    searchable_text=(
                        "创新竞赛立项模板 innovation competition template proposal pitch storytelling team collaboration"
                    ),
                    indexed_at=datetime.now(timezone.utc),
                )
            )

            settings.experimental_local_knowledge_enabled = True
            settings.experimental_local_knowledge_index_db = str(db_path)
            settings.experimental_local_knowledge_top_k = 2
            try:
                task = AgentTaskEnvelope(
                    contract_version="1.0",
                    task_id="run-recommender-local-001",
                    session_id="session-recommender-local-001",
                    task_type="competition_recommendation",
                    requested_by="user",
                    priority="normal",
                    objective="Recommend competitions with local grounding.",
                    payload={
                        "profile": {
                            "grade": "junior",
                            "direction": "innovation",
                            "ability_tags": ["prototype", "presentation"],
                        }
                    },
                    constraints=[],
                    dry_run=False,
                    created_at=datetime.now(timezone.utc),
                )
                ledger = ResearchLedger(
                    contract_version="1.0",
                    ledger_id="ledger-session-recommender-local-001",
                    session_id=task.session_id,
                    topic="competition_recommendation",
                    research_question=task.objective,
                    status="active",
                    scope=ResearchScope(),
                    task_history=[],
                    source_registry=[],
                    evidence_log=[],
                    created_at=datetime.now(timezone.utc),
                )

                output = CompetitionRecommenderAgent().run(task, ledger)
            finally:
                settings.experimental_local_knowledge_enabled = previous_enabled
                settings.experimental_local_knowledge_index_db = previous_db
                settings.experimental_local_knowledge_top_k = previous_top_k

        joined_reasons = " ".join(reason for item in output["recommendations"] for reason in item["reasons"])
        joined_risks = " ".join(output["risk_overview"])
        self.assertIn("Local knowledge:", joined_reasons)
        self.assertIn("Local grounding used:", joined_risks)


if __name__ == "__main__":
    unittest.main()
