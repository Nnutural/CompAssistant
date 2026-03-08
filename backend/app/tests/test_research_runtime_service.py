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
from app.schemas.research_runtime import AgentResult, AgentTaskEnvelope  # noqa: E402
from app.services.research_runtime_service import ResearchRuntimeService  # noqa: E402


class ResearchRuntimeServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        repository = LedgerRepository(self.temp_dir.name)
        self.service = ResearchRuntimeService(repository=repository)
        self.task = self._load_task_example()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _load_task_example(self) -> AgentTaskEnvelope:
        path = REPO_ROOT / "docs" / "examples" / "research-runtime-input.minimal.json"
        with path.open("r", encoding="utf-8-sig") as handle:
            return AgentTaskEnvelope.model_validate(json.load(handle))

    def test_run_task_updates_ledger_and_returns_structured_result(self) -> None:
        result = self.service.run_task(self.task)
        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.status, "completed")
        self.assertGreaterEqual(len(result.findings), 1)

        ledger = self.service.get_ledger("ledger-session-phase2-001")
        self.assertIsNotNone(ledger)
        self.assertGreaterEqual(len(ledger.task_history), 1)
        self.assertGreaterEqual(len(ledger.evidence_log), 1)
        self.assertGreaterEqual(len(ledger.final_artifacts), 1)