"""AI crawler scaffold package.

This package is intentionally decoupled from the existing runtime, APIs, and
frontend. It only provides a minimal placeholder structure for future work.
"""

from .schemas import (
    CrawlDocument,
    CrawlRequest,
    CrawlResult,
    KnowledgeRecord,
    NormalizedDocument,
    RawDocument,
)
from .source_manifest import SourceManifestEntry, list_source_manifest_entries
from .service import CrawlerService, LocalDocumentIngestionService

__all__ = [
    "CrawlDocument",
    "CrawlRequest",
    "CrawlResult",
    "CrawlerService",
    "KnowledgeRecord",
    "LocalDocumentIngestionService",
    "NormalizedDocument",
    "RawDocument",
    "SourceManifestEntry",
    "list_source_manifest_entries",
]
