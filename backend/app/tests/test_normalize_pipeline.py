import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.crawler.pipelines.normalize_pipeline import NormalizePipeline  # noqa: E402
from app.crawler.schemas import RawDocument  # noqa: E402


class NormalizePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = NormalizePipeline()

    def test_html_document_is_normalized(self) -> None:
        raw_document = RawDocument(
            doc_id="policy-001",
            source_type="policy",
            source_name="gov-policy-demo",
            url="https://example.com/policy",
            fetch_method="http_get",
            raw_content_type="text/html",
            raw_text=(
                "<html><head><title>Innovation Policy</title></head>"
                "<body><h1>Innovation Policy</h1><p>Students must complete registration.</p></body></html>"
            ),
            raw_ref="raw/policy-001.json",
            fetched_at=datetime.now(timezone.utc),
            metadata={"tags": ["policy", "innovation"], "region": "CN"},
        )

        normalized = self.pipeline.run(raw_document)
        record = self.pipeline.build_knowledge_record(normalized)

        self.assertEqual(normalized.title, "Innovation Policy")
        self.assertIn("Students must complete registration.", normalized.content_text)
        self.assertEqual(normalized.source_type, "policy")
        self.assertIn("policy", normalized.tags)
        self.assertEqual(record.record_id, "knowledge-policy-001")
        self.assertIn("Innovation Policy", record.searchable_text)

    def test_json_competition_document_is_normalized(self) -> None:
        raw_document = RawDocument(
            doc_id="competition-001",
            source_type="competition",
            source_name="competition-catalog-static",
            url="https://example.com/competition",
            fetch_method="local_json_extract",
            raw_content_type="application/json",
            raw_text=json.dumps(
                {
                    "name": "National Innovation Challenge",
                    "description": "A competition for innovation and product design.",
                    "suggestions": ["Prepare a demo", "Form a team"],
                    "field": "innovation",
                    "difficulty": "medium",
                    "level": "A",
                },
                ensure_ascii=False,
            ),
            raw_ref="raw/competition-001.json",
            fetched_at=datetime.now(timezone.utc),
        )

        normalized = self.pipeline.run(raw_document)

        self.assertEqual(normalized.title, "National Innovation Challenge")
        self.assertIn("Form a team", normalized.content_text)
        self.assertIn("innovation", normalized.tags)


if __name__ == "__main__":
    unittest.main()
