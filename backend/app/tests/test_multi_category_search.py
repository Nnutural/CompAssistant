import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.crawler.schemas import KnowledgeRecord  # noqa: E402
from app.retrieval.search_service import DocumentSearchService  # noqa: E402
from app.retrieval.sqlite_index_store import SQLiteIndexStore  # noqa: E402


class MultiCategorySearchTests(unittest.TestCase):
    def test_search_supports_multi_category_and_channel_filters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteIndexStore(db_path=Path(temp_dir) / "knowledge.sqlite3")
            service = DocumentSearchService(store=store)
            records = [
                KnowledgeRecord(
                    record_id="knowledge-fund-guide-001",
                    doc_id="fund-guide-001",
                    title="NSFC Guide",
                    summary="Fund application guidance.",
                    content_text="Innovation application guide and proposal requirements.",
                    source_type="fund_guide",
                    source_channel="public_web",
                    source_name="nsfc-guide",
                    implementation_status="implemented",
                    tags=["fund_guide", "innovation"],
                    publish_time=datetime.now(timezone.utc),
                    url="https://example.com/fund-guide",
                    searchable_text="NSFC Guide Innovation application guide and proposal requirements.",
                    indexed_at=datetime.now(timezone.utc),
                ),
                KnowledgeRecord(
                    record_id="knowledge-template-001",
                    doc_id="template-001",
                    title="Proposal Template",
                    summary="Competition template guidance.",
                    content_text="Template for competition proposal and team preparation.",
                    source_type="excellent_template",
                    source_channel="local_file",
                    source_name="template-curated",
                    implementation_status="importer",
                    tags=["excellent_template", "competition"],
                    publish_time=datetime.now(timezone.utc),
                    url="local://template",
                    searchable_text="Proposal Template competition proposal and team preparation.",
                    indexed_at=datetime.now(timezone.utc),
                ),
                KnowledgeRecord(
                    record_id="knowledge-competition-001",
                    doc_id="competition-001",
                    title="Service Outsourcing Competition",
                    summary="Competition notice.",
                    content_text="Innovation competition notice and organizer guidance.",
                    source_type="competition_info",
                    source_channel="public_web",
                    source_name="moe-competition",
                    implementation_status="implemented",
                    tags=["competition_info", "innovation"],
                    publish_time=datetime.now(timezone.utc),
                    url="https://example.com/competition",
                    searchable_text="Service Outsourcing Competition innovation competition notice and organizer guidance.",
                    indexed_at=datetime.now(timezone.utc),
                ),
            ]
            for item in records:
                store.upsert(item)

            hits = service.search_documents(
                "innovation competition guide",
                filters={"source_types": ["fund_guide", "competition_info"], "source_channel": "public_web"},
                top_k=5,
            )

            self.assertEqual([hit.record_id for hit in hits], ["knowledge-fund-guide-001", "knowledge-competition-001"])


if __name__ == "__main__":
    unittest.main()
