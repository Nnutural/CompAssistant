from __future__ import annotations

import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.crawler.providers.http_provider import HttpCrawlerProvider  # noqa: E402
from app.crawler.service import LocalDocumentIngestionService  # noqa: E402
from app.crawler.sources.competition_catalog_source import CompetitionCatalogSource  # noqa: E402
from app.retrieval.search_service import search_documents  # noqa: E402


POLICY_SOURCE_URL = "https://www.moe.gov.cn/jyb_xwfb/s6052/moe_838/202110/t20211013_571912.html"


def main() -> None:
    provider = HttpCrawlerProvider(timeout_seconds=20.0)
    competition_source = CompetitionCatalogSource()
    ingestion_service = LocalDocumentIngestionService()

    policy_document = provider.fetch_document(
        source_type="policy",
        source_name="moe_innovation_policy",
        url=POLICY_SOURCE_URL,
        metadata={
            "tags": ["policy", "innovation", "competition"],
            "region": "CN",
            "school_or_org": "Ministry of Education",
        },
    )
    competition_documents = competition_source.load_raw_documents(limit=1)
    batch = ingestion_service.ingest_documents([policy_document, *competition_documents])

    hits = search_documents("大学生 创新创业 竞赛 政策", top_k=5)
    payload = {
        "ingested_raw_documents": [item.doc_id for item in batch.raw_documents],
        "normalized_documents": [item.doc_id for item in batch.normalized_documents],
        "knowledge_records": [item.record_id for item in batch.knowledge_records],
        "search_hits": [item.model_dump(mode="json") for item in hits],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
