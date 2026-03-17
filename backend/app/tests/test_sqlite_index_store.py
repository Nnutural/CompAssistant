import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.crawler.schemas import KnowledgeRecord  # noqa: E402
from app.retrieval.sqlite_index_store import SQLiteIndexStore  # noqa: E402


class SQLiteIndexStoreTests(unittest.TestCase):
    def test_upsert_search_and_get_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteIndexStore(db_path=Path(temp_dir) / "knowledge.sqlite3")
            record = KnowledgeRecord(
                record_id="knowledge-policy-001",
                doc_id="policy-001",
                title="Innovation Competition Policy",
                summary="Registration and eligibility guidance.",
                content_text="Innovation competition registration policy and eligibility rules.",
                source_type="national_policy",
                source_channel="public_web",
                source_name="gov-policy-demo",
                implementation_status="implemented",
                tags=["national_policy", "competition_info"],
                publish_time=datetime.now(timezone.utc),
                url="https://example.com/policy",
                searchable_text="Innovation Competition Policy Registration and eligibility guidance.",
                indexed_at=datetime.now(timezone.utc),
            )

            store.upsert(record)
            hits = store.search_documents("eligibility policy", top_k=3)
            loaded = store.get_document("knowledge-policy-001")

            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0].record_id, "knowledge-policy-001")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.title, "Innovation Competition Policy")
            self.assertEqual(hits[0].source_channel, "public_web")


if __name__ == "__main__":
    unittest.main()
