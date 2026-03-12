from __future__ import annotations

from ..schemas import CrawlResult


class PlaceholderCrawlStore:
    name = "placeholder_store"

    def __init__(self) -> None:
        self.saved_results: list[CrawlResult] = []

    def save(self, result: CrawlResult) -> None:
        self.saved_results.append(result)
