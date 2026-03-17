import sys
import tempfile
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.crawler.pipelines.normalize_pipeline import NormalizePipeline  # noqa: E402
from app.crawler.providers.http_provider import HttpCrawlerProvider  # noqa: E402
from app.crawler.service import LocalDocumentIngestionService  # noqa: E402
from app.crawler.sources.competition_catalog_source import CompetitionCatalogSource  # noqa: E402
from app.crawler.storage.file_system_store import FileSystemDocumentStore  # noqa: E402
from app.retrieval.sqlite_index_store import SQLiteIndexStore  # noqa: E402


class LocalKnowledgeIntegrationTests(unittest.TestCase):
    def test_http_and_competition_sources_flow_into_local_index(self) -> None:
        fixture_dir = REPO_ROOT / "backend" / "app" / "tests" / "fixtures" / "crawler"
        with tempfile.TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir) / "local_knowledge"
            file_store = FileSystemDocumentStore(root_dir=data_root)
            index_store = SQLiteIndexStore(db_path=data_root / "knowledge.sqlite3")
            service = LocalDocumentIngestionService(
                file_store=file_store,
                normalize_pipeline=NormalizePipeline(),
                index_store=index_store,
            )
            provider = HttpCrawlerProvider(timeout_seconds=5.0)
            competition_source = CompetitionCatalogSource(
                data_path=REPO_ROOT / "backend" / "data" / "competitions.json"
            )

            server, base_url = _start_static_server(fixture_dir)
            try:
                policy_raw = provider.fetch_document(
                    source_type="national_policy",
                    source_name="gov-policy-demo",
                    url=f"{base_url}/policy_sample.html",
                    metadata={"tags": ["policy", "competition"], "region": "CN", "school_or_org": "MOE"},
                )
                competition_raw = competition_source.load_raw_documents(limit=1)[0]
                batch = service.ingest_documents([policy_raw, competition_raw])
            finally:
                server.shutdown()
                server.server_close()

            self.assertEqual(len(batch.raw_documents), 2)
            self.assertEqual(len(batch.normalized_documents), 2)
            self.assertEqual(len(batch.knowledge_records), 2)
            self.assertTrue((data_root / "raw" / f"{policy_raw.doc_id}.json").exists())
            self.assertTrue((data_root / "normalized" / f"{policy_raw.doc_id}.json").exists())

            hits = index_store.search_documents("competition policy", top_k=5)
            self.assertGreaterEqual(len(hits), 1)
            self.assertTrue(any(hit.source_type == "national_policy" for hit in hits))


def _start_static_server(directory: Path) -> tuple[ThreadingHTTPServer, str]:
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}"


if __name__ == "__main__":
    unittest.main()
