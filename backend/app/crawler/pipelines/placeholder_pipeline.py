from __future__ import annotations

from ..schemas import CrawlResult


class PlaceholderCrawlerPipeline:
    name = "placeholder_pipeline"

    def run(self, result: CrawlResult) -> CrawlResult:
        notes = list(result.notes)
        notes.append("Placeholder pipeline executed.")
        return result.model_copy(update={"notes": notes})
