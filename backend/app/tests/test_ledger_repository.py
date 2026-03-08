import json
import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.repositories.ledger_repository import LedgerRepository  # noqa: E402
from app.schemas.research_runtime import ResearchLedger  # noqa: E402


class LedgerRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = LedgerRepository(self.temp_dir.name)
        self.ledger = self._load_ledger_example()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _load_ledger_example(self) -> ResearchLedger:
        path = REPO_ROOT / "docs" / "examples" / "research-ledger.minimal.json"
        with path.open("r", encoding="utf-8-sig") as handle:
            return ResearchLedger.model_validate(json.load(handle))

    def test_create_get_update_and_list(self) -> None:
        created = self.repository.create(self.ledger)
        self.assertEqual(created.ledger_id, self.ledger.ledger_id)

        fetched = self.repository.get(self.ledger.ledger_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.topic, self.ledger.topic)

        fetched.open_questions.append("需要补充 Phase 3 真实调度。")
        self.repository.update(fetched)
        updated = self.repository.get(self.ledger.ledger_id)
        self.assertIn("需要补充 Phase 3 真实调度。", updated.open_questions)

        ledgers = self.repository.list()
        self.assertEqual(len(ledgers), 1)
        self.assertEqual(ledgers[0].ledger_id, self.ledger.ledger_id)