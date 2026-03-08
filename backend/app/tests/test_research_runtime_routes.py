import json
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.routes.research_runtime import get_research_runtime_service  # noqa: E402
from app.main import create_application  # noqa: E402
from app.repositories.ledger_repository import LedgerRepository  # noqa: E402
from app.schemas.research_runtime import AgentResult, ResearchLedger  # noqa: E402
from app.services.research_runtime_service import ResearchRuntimeService  # noqa: E402


class ResearchRuntimeRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        repository = LedgerRepository(self.temp_dir.name)
        self.service = ResearchRuntimeService(repository=repository, runtime_mode='mock')
        self.app = create_application()
        self.app.dependency_overrides[get_research_runtime_service] = lambda: self.service
        self.client = TestClient(self.app)
        self.task_payload = self._load_example('research-runtime-input.minimal.json')

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        self.temp_dir.cleanup()

    def _load_example(self, filename: str) -> dict:
        path = REPO_ROOT / 'docs' / 'examples' / filename
        with path.open('r', encoding='utf-8-sig') as handle:
            return json.load(handle)

    def test_run_route_and_ledger_route(self) -> None:
        run_response = self.client.post('/api/research-runtime/run', json=self.task_payload)
        self.assertEqual(run_response.status_code, 200)
        result = AgentResult.model_validate(run_response.json())
        self.assertEqual(result.status, 'completed')
        self.assertGreaterEqual(len(result.findings), 1)

        ledger_response = self.client.get('/api/research-runtime/ledger/ledger-session-phase2-001')
        self.assertEqual(ledger_response.status_code, 200)
        ledger = ResearchLedger.model_validate(ledger_response.json())
        self.assertGreaterEqual(len(ledger.task_history), 1)
        self.assertGreaterEqual(len(ledger.evidence_log), 1)


if __name__ == '__main__':
    unittest.main()
