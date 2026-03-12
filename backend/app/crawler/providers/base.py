from __future__ import annotations

from abc import ABC, abstractmethod

from ..schemas import CrawlRequest, CrawlResult


class BaseCrawlerProvider(ABC):
    name = "base"

    @abstractmethod
    def execute(self, request: CrawlRequest) -> CrawlResult:
        raise NotImplementedError
