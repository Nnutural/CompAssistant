import json
import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


MANIFEST_PATH = REPO_ROOT / "docs" / "data-manifest.json"
REQUIRED_ITEM_KEYS = {
    "name",
    "layer",
    "status",
    "source_type",
    "source_of_truth",
    "persisted",
    "schema_ref",
    "code_refs",
    "consumers",
    "notes",
}
ALLOWED_STATUSES = {"implemented", "partial", "placeholder", "unimplemented"}


class DataManifestTests(unittest.TestCase):
    def test_manifest_exists_and_is_parseable(self) -> None:
        self.assertTrue(MANIFEST_PATH.exists(), "docs/data-manifest.json must exist")
        with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("version"), 1)
        items = payload.get("items")
        self.assertIsInstance(items, list)
        self.assertGreater(len(items), 0)

        names: set[str] = set()
        for item in items:
            self.assertEqual(set(item.keys()), REQUIRED_ITEM_KEYS)
            self.assertIn(item["status"], ALLOWED_STATUSES)
            self.assertIsInstance(item["code_refs"], list)
            self.assertTrue(item["code_refs"])
            self.assertIsInstance(item["consumers"], list)
            self.assertTrue(item["notes"])
            self.assertNotIn(item["name"], names)
            names.add(item["name"])

            schema_ref = item["schema_ref"]
            if schema_ref is not None:
                self.assertTrue((REPO_ROOT / schema_ref).exists(), f"Missing schema_ref path: {schema_ref}")

            for ref in item["code_refs"]:
                self.assertTrue((REPO_ROOT / ref).exists(), f"Missing code_ref path: {ref}")

        self.assertIn("research_ledger", names)
        self.assertIn("agent_task_create_request", names)
        self.assertIn("crawler_placeholder_contracts", names)
        self.assertIn("crawler_source_taxonomy", names)
        self.assertIn("phase5h_source_manifest", names)


if __name__ == "__main__":
    unittest.main()
