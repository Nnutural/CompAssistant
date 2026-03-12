"""AI crawler scaffold package.

This package is intentionally decoupled from the existing runtime, APIs, and
frontend. It only provides a minimal placeholder structure for future work.
"""

from .schemas import CrawlDocument, CrawlRequest, CrawlResult
from .service import CrawlerService

__all__ = ["CrawlDocument", "CrawlRequest", "CrawlResult", "CrawlerService"]
