import json
import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.crawler.source_manifest import list_source_manifest_entries  # noqa: E402
from app.crawler.taxonomy import (  # noqa: E402
    ALL_DOCUMENT_SOURCE_TYPES,
    ALL_IMPLEMENTATION_STATUSES,
    ALL_SOURCE_CHANNELS,
)


DOCS_MANIFEST_PATH = REPO_ROOT / "docs" / "data-source-manifest.json"


class Phase5HSourceManifestTests(unittest.TestCase):
    def test_docs_source_manifest_matches_code_manifest(self) -> None:
        self.assertTrue(DOCS_MANIFEST_PATH.exists())
        with DOCS_MANIFEST_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        self.assertEqual(payload["version"], 1)
        self.assertEqual(
            {item["key"] for item in payload["content_categories"]},
            set(ALL_DOCUMENT_SOURCE_TYPES),
        )
        self.assertEqual(
            {item["key"] for item in payload["source_channels"]},
            set(ALL_SOURCE_CHANNELS),
        )
        self.assertEqual(
            set(payload["implementation_statuses"]),
            set(ALL_IMPLEMENTATION_STATUSES),
        )

        code_entries = list_source_manifest_entries()
        docs_sources = payload["sources"]
        self.assertEqual(len(code_entries), len(docs_sources))

        docs_by_id = {item["source_id"]: item for item in docs_sources}
        code_by_id = {item.source_id: item for item in code_entries}
        self.assertEqual(set(docs_by_id), set(code_by_id))
        for source_id, code_entry in code_by_id.items():
            docs_entry = docs_by_id[source_id]
            self.assertEqual(docs_entry["source_type"], code_entry.source_type)
            self.assertEqual(docs_entry["source_channel"], code_entry.source_channel)
            self.assertEqual(docs_entry["implementation_status"], code_entry.implementation_status)
            self.assertEqual(docs_entry["access_strategy"], code_entry.access_strategy)

    def test_all_ten_categories_are_covered(self) -> None:
        entries = list_source_manifest_entries()
        covered = {entry.source_type for entry in entries}
        self.assertEqual(covered, set(ALL_DOCUMENT_SOURCE_TYPES))
        for category in ALL_DOCUMENT_SOURCE_TYPES:
            self.assertTrue(any(entry.source_type == category for entry in entries), category)


if __name__ == "__main__":
    unittest.main()
