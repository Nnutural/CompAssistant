import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.crawler import CrawlerService  # noqa: E402
from app.crawler.registry import list_providers  # noqa: E402
from app.crawler.schemas import CrawlRequest  # noqa: E402


class CrawlerScaffoldTests(unittest.TestCase):
    def test_placeholder_service_returns_not_implemented_result(self) -> None:
        service = CrawlerService()
        request = CrawlRequest(
            request_id="crawl-001",
            source="placeholder",
            target="competition-site",
            entrypoint="https://example.com",
        )

        result = service.run(request)

        self.assertEqual(result.request_id, "crawl-001")
        self.assertEqual(result.provider, "placeholder")
        self.assertEqual(result.status, "not_implemented")
        self.assertEqual(result.documents, [])
        self.assertIn("Placeholder pipeline executed.", result.notes)

    def test_registry_lists_placeholder_provider(self) -> None:
        self.assertEqual(list_providers(), ["placeholder"])


if __name__ == "__main__":
    unittest.main()
