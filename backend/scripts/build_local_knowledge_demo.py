from __future__ import annotations

import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.crawler.importers import FileDocumentImporter, StructuredDataImporter, WeChatArticleImporter  # noqa: E402
from app.crawler.providers.http_provider import HttpCrawlerProvider  # noqa: E402
from app.crawler.service import LocalDocumentIngestionService  # noqa: E402
from app.crawler.source_manifest import list_source_manifest_entries  # noqa: E402
from app.crawler.sources.competition_catalog_source import CompetitionCatalogSource  # noqa: E402
from app.retrieval.search_service import search_documents  # noqa: E402


IMPORT_ROOT = BACKEND_ROOT / "data" / "local_knowledge_imports" / "phase5h"

PUBLIC_SOURCE_METADATA: dict[str, dict[str, object]] = {
    "moe_innovation_policy_public_web": {
        "tags": ["innovation", "entrepreneurship", "policy"],
        "region": "CN",
        "school_or_org": "Ministry of Education",
    },
    "nsfc_regulation_public_web": {
        "tags": ["law", "regulation", "funding"],
        "region": "CN",
        "school_or_org": "NSFC",
    },
    "moe_employment_notice_public_web": {
        "tags": ["employment", "graduation", "recruitment"],
        "region": "CN",
        "school_or_org": "Ministry of Education",
    },
    "nsfc_guide_public_web": {
        "tags": ["fund", "guide", "application"],
        "region": "CN",
        "school_or_org": "NSFC",
    },
    "moe_approved_projects_public_web": {
        "title": "西安交通大学获批项目公开通知",
        "summary": "高校公开通知页，说明创新创业训练计划项目立项结果与后续管理要求。",
        "tags": ["approved_project", "innovation_training", "project_notice"],
        "region": "CN",
        "school_or_org": "Xi'an Jiaotong University",
    },
    "moe_internet_plus_competition_public_web": {
        "tags": ["competition", "service_outsourcing", "innovation"],
        "region": "CN",
        "school_or_org": "Ministry of Education",
    },
}

FILE_IMPORT_DEFINITIONS = (
    {
        "path": IMPORT_ROOT / "excellent_template.md",
        "source_type": "excellent_template",
        "source_name": "excellent_template_curated",
        "source_channel": "local_file",
        "metadata": {
            "title": "省级竞赛立项书模板",
            "tags": ["template", "proposal", "competition"],
            "school_or_org": "CompAssistant Curated Desk",
            "region": "CN",
        },
    },
    {
        "path": IMPORT_ROOT / "experience_sharing.txt",
        "source_type": "experience_sharing",
        "source_name": "experience_sharing_curated",
        "source_channel": "local_file",
        "metadata": {
            "tags": ["experience", "pitch", "preparation"],
            "school_or_org": "CompAssistant Curated Desk",
            "region": "CN",
        },
    },
)

STRUCTURED_IMPORT_DEFINITIONS = (
    {
        "path": IMPORT_ROOT / "social_hotspots.json",
        "source_type": "social_hotspot",
        "source_name": "social_hotspot_curated",
        "source_channel": "manual_import",
    },
    {
        "path": IMPORT_ROOT / "award_winning_works.csv",
        "source_type": "award_winning_work",
        "source_name": "award_winning_works_curated",
        "source_channel": "manual_import",
    },
)

WECHAT_IMPORT_DEFINITIONS = (
    {
        "path": IMPORT_ROOT / "wechat_article_experience.md",
        "source_type": "experience_sharing",
        "source_name": "wechat_experience_article",
        "metadata": {
            "tags": ["wechat", "experience", "storytelling"],
            "school_or_org": "Manual WeChat Import",
            "region": "CN",
        },
    },
)


def main() -> None:
    provider = HttpCrawlerProvider(timeout_seconds=20.0)
    competition_source = CompetitionCatalogSource()
    file_importer = FileDocumentImporter()
    structured_importer = StructuredDataImporter()
    wechat_importer = WeChatArticleImporter(
        file_importer=file_importer,
        structured_importer=structured_importer,
    )
    ingestion_service = LocalDocumentIngestionService()

    raw_documents = []
    for entry in list_source_manifest_entries():
        if entry.implementation_status != "implemented":
            continue
        if entry.access_strategy != "static_http_source":
            continue
        raw_documents.append(
            provider.fetch_document(
                doc_id=entry.source_id,
                source_type=entry.source_type,
                source_channel=entry.source_channel,
                source_name=entry.source_name,
                implementation_status=entry.implementation_status,
                url=str(entry.entrypoint),
                metadata=PUBLIC_SOURCE_METADATA.get(entry.source_id, {}),
            )
        )

    raw_documents.extend(competition_source.load_raw_documents(limit=3))

    for definition in STRUCTURED_IMPORT_DEFINITIONS:
        raw_documents.extend(
            structured_importer.import_file(
                definition["path"],
                source_type=str(definition["source_type"]),
                source_name=str(definition["source_name"]),
                source_channel=str(definition["source_channel"]),
                implementation_status="importer",
            )
        )

    for definition in FILE_IMPORT_DEFINITIONS:
        raw_documents.extend(
            file_importer.import_file(
                definition["path"],
                source_type=str(definition["source_type"]),
                source_name=str(definition["source_name"]),
                source_channel=str(definition["source_channel"]),
                implementation_status="importer",
                metadata=dict(definition["metadata"]),
            )
        )

    for definition in WECHAT_IMPORT_DEFINITIONS:
        raw_documents.extend(
            wechat_importer.import_article(
                definition["path"],
                source_type=str(definition["source_type"]),
                source_name=str(definition["source_name"]),
                metadata=dict(definition["metadata"]),
            )
        )

    batch = ingestion_service.ingest_documents(raw_documents)
    hits = search_documents(
        "innovation competition fund project template experience employment",
        top_k=10,
    )

    categories = sorted({item.source_type for item in batch.knowledge_records})
    payload = {
        "ingested_raw_documents": [item.doc_id for item in batch.raw_documents],
        "normalized_documents": [item.doc_id for item in batch.normalized_documents],
        "knowledge_records": [item.record_id for item in batch.knowledge_records],
        "category_count": len(categories),
        "categories": categories,
        "search_hits": [item.model_dump(mode="json") for item in hits],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
