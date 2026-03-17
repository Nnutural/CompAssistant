import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.crawler.schemas import KnowledgeRecord  # noqa: E402
from app.retrieval.search_service import DocumentSearchService, get_document, search_documents  # noqa: E402
from app.retrieval.sqlite_index_store import SQLiteIndexStore  # noqa: E402


class RetrievalServiceTests(unittest.TestCase):
    def test_search_service_returns_structured_hits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteIndexStore(db_path=Path(temp_dir) / "knowledge.sqlite3")
            service = DocumentSearchService(store=store)
            store.upsert(
                KnowledgeRecord(
                    record_id="knowledge-competition-001",
                    doc_id="competition-001",
                    title="National Innovation Challenge",
                    summary="Competition briefing and preparation tips.",
                    content_text="Innovation challenge competition briefing and team preparation guidance.",
                    source_type="competition_info",
                    source_channel="local_file",
                    source_name="competition-catalog-static",
                    implementation_status="implemented",
                    tags=["competition_info", "innovation"],
                    publish_time=datetime.now(timezone.utc),
                    url="https://example.com/competition",
                    searchable_text="National Innovation Challenge competition briefing and team preparation guidance.",
                    indexed_at=datetime.now(timezone.utc),
                )
            )

            hits = service.search_documents(
                "innovation challenge",
                filters={"source_type": "competition_info", "source_channel": "local_file"},
                top_k=2,
            )
            loaded = get_document("knowledge-competition-001", service=service)
            hits_via_function = search_documents("innovation", service=service)

            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0].source_type, "competition_info")
            self.assertEqual(hits[0].source_channel, "local_file")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.doc_id, "competition-001")
            self.assertEqual(hits_via_function[0].record_id, "knowledge-competition-001")


if __name__ == "__main__":
    unittest.main()
