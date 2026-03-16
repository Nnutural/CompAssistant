import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.crawler.schemas import KnowledgeRecord, NormalizedDocument, RawDocument  # noqa: E402


class CrawlerDocumentSchemaTests(unittest.TestCase):
    def test_raw_document_requires_raw_text_or_raw_ref(self) -> None:
        with self.assertRaises(ValidationError):
            RawDocument(
                doc_id="policy-001",
                source_type="policy",
                source_name="gov-policy-demo",
                url="https://example.com/policy",
                fetch_method="http_get",
                raw_content_type="text/html",
                fetched_at=datetime.now(timezone.utc),
            )

    def test_normalized_and_knowledge_records_validate(self) -> None:
        normalized = NormalizedDocument(
            doc_id="policy-001",
            source_type="policy",
            source_name="gov-policy-demo",
            url="https://example.com/policy",
            title="Innovation Competition Policy",
            publish_time=datetime.now(timezone.utc),
            content_text="Eligibility rules and registration guidance for innovation competitions.",
            tags=["policy", "competition", "policy"],
            region="CN",
            school_or_org="Ministry of Education",
            raw_ref="raw/policy-001.json",
            checksum="a" * 64,
            language="en",
            collected_at=datetime.now(timezone.utc),
            normalized_metadata={"sample": True},
        )
        record = KnowledgeRecord(
            record_id="knowledge-policy-001",
            doc_id=normalized.doc_id,
            title=normalized.title,
            summary="Eligibility rules and registration guidance.",
            content_text=normalized.content_text,
            source_type=normalized.source_type,
            source_name=normalized.source_name,
            tags=normalized.tags,
            publish_time=normalized.publish_time,
            url=normalized.url,
            searchable_text=f"{normalized.title}\n{normalized.content_text}",
            indexed_at=datetime.now(timezone.utc),
        )

        self.assertEqual(normalized.tags, ["policy", "competition"])
        self.assertEqual(record.source_type, "policy")


if __name__ == "__main__":
    unittest.main()
