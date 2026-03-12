from __future__ import annotations

from .base import BaseCrawlerProvider
from ..schemas import CrawlRequest, CrawlResult


class PlaceholderCrawlerProvider(BaseCrawlerProvider):
    name = "placeholder"

    def execute(self, request: CrawlRequest) -> CrawlResult:
        return CrawlResult(
            request_id=request.request_id,
            provider=self.name,
            status="not_implemented",
            notes=[
                "AI crawler scaffold placeholder only.",
                "No real crawling, login, or network extraction is implemented.",
            ],
        )
