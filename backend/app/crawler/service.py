from __future__ import annotations

from .interfaces import CrawlerPipeline, CrawlerStore
from .pipelines.placeholder_pipeline import PlaceholderCrawlerPipeline
from .registry import DEFAULT_PROVIDER, get_provider
from .schemas import CrawlRequest, CrawlResult
from .storage.placeholder_store import PlaceholderCrawlStore


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
