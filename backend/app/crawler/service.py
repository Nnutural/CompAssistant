from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .interfaces import CrawlerPipeline, CrawlerStore
from .pipelines.normalize_pipeline import NormalizePipeline
from .pipelines.placeholder_pipeline import PlaceholderCrawlerPipeline
from .registry import DEFAULT_PROVIDER, get_provider
from .schemas import CrawlRequest, CrawlResult, KnowledgeRecord, NormalizedDocument, RawDocument
from .storage.file_system_store import FileSystemDocumentStore
from .storage.placeholder_store import PlaceholderCrawlStore

if TYPE_CHECKING:
    from app.retrieval.sqlite_index_store import SQLiteIndexStore


class CrawlerService:
    """Minimal placeholder service for a future crawler subsystem."""

    def __init__(
        self,
        *,
        provider_name: str = DEFAULT_PROVIDER,
        pipeline: CrawlerPipeline | None = None,
        store: CrawlerStore | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.pipeline = pipeline or PlaceholderCrawlerPipeline()
        self.store = store or PlaceholderCrawlStore()

    def run(self, request: CrawlRequest) -> CrawlResult:
        provider = get_provider(self.provider_name)
        result = provider.execute(request)
        result = self.pipeline.run(result)
        self.store.save(result)
        return result


@dataclass
class LocalIngestionBatch:
    raw_documents: list[RawDocument] = field(default_factory=list)
    normalized_documents: list[NormalizedDocument] = field(default_factory=list)
    knowledge_records: list[KnowledgeRecord] = field(default_factory=list)


class LocalDocumentIngestionService:
    """Experimental local-only document ingestion path."""

    def __init__(
        self,
        *,
        file_store: FileSystemDocumentStore | None = None,
        normalize_pipeline: NormalizePipeline | None = None,
        index_store: "SQLiteIndexStore" | None = None,
    ) -> None:
        if index_store is None:
            from app.retrieval.sqlite_index_store import SQLiteIndexStore

            index_store = SQLiteIndexStore()
        self.file_store = file_store or FileSystemDocumentStore()
        self.normalize_pipeline = normalize_pipeline or NormalizePipeline()
        self.index_store = index_store

    def ingest_documents(self, raw_documents: list[RawDocument]) -> LocalIngestionBatch:
        batch = LocalIngestionBatch()
        for document in raw_documents:
            persisted_raw = self.file_store.save_raw(document)
            normalized = self.normalize_pipeline.run(persisted_raw)
            self.file_store.save_normalized(normalized)
            record = self.normalize_pipeline.build_knowledge_record(normalized)
            self.index_store.upsert(record)
            batch.raw_documents.append(persisted_raw)
            batch.normalized_documents.append(normalized)
            batch.knowledge_records.append(record)
        return batch
