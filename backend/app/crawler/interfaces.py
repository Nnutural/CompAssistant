from __future__ import annotations

from typing import Protocol

from .schemas import CrawlRequest, CrawlResult


class CrawlerProvider(Protocol):
    name: str

    def execute(self, request: CrawlRequest) -> CrawlResult:
        """Run a crawl request and return a placeholder result."""


class CrawlerPipeline(Protocol):
    name: str

    def run(self, result: CrawlResult) -> CrawlResult:
        """Post-process a crawl result."""


class CrawlerStore(Protocol):
    name: str

    def save(self, result: CrawlResult) -> None:
        """Persist or bridge a crawl result."""
