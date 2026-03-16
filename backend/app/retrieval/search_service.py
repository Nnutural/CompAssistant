from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.crawler.schemas import KnowledgeRecord

from .schemas import DocumentSearchFilters, DocumentSearchHit
from .sqlite_index_store import SQLiteIndexStore


class DocumentSearchService:
    def __init__(self, store: SQLiteIndexStore | None = None, *, db_path: str | Path | None = None) -> None:
        self.store = store or SQLiteIndexStore(db_path=db_path or settings.experimental_local_knowledge_index_db or None)

    def search_documents(
        self,
        query: str,
        filters: DocumentSearchFilters | dict | None = None,
        top_k: int = 5,
    ) -> list[DocumentSearchHit]:
        return self.store.search_documents(query, filters=filters, top_k=top_k)

    def get_document(self, record_id: str) -> KnowledgeRecord | None:
        return self.store.get_document(record_id)


def search_documents(
    query: str,
    filters: DocumentSearchFilters | dict | None = None,
    top_k: int = 5,
    *,
    service: DocumentSearchService | None = None,
) -> list[DocumentSearchHit]:
    active_service = service or DocumentSearchService()
    return active_service.search_documents(query, filters=filters, top_k=top_k)


def get_document(record_id: str, *, service: DocumentSearchService | None = None) -> KnowledgeRecord | None:
    active_service = service or DocumentSearchService()
    return active_service.get_document(record_id)
