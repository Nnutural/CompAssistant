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
from app.schemas.research_runtime import AgentResult, AgentTaskEnvelope, LedgerTaskEntry  # noqa: E402
from app.services.research_runtime_service import ResearchRuntimeService  # noqa: E402


class _FakeSDKRuntime:
    def __init__(self, available: bool, result: AgentResult | None = None):
        self.available = available
        self._result = result

    def is_available(self) -> bool:
        return self.available

    def run(self, task, ledger):
        if self._result is None:
            raise RuntimeError('SDK runtime was not configured for this test')
        ledger.task_history.append(
            LedgerTaskEntry(
                task_id=f'{task.task_id}:sdk',
                agent='manager',
                status='completed',
                summary='Agents SDK test runtime updated the ledger.',
            )
        )
        ledger.synthesis_notes.append('runtime mode: agents_sdk')
        ledger.updated_at = self._result.completed_at
        return self._result, ledger


class ResearchRuntimeServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = LedgerRepository(self.temp_dir.name)
        self.task = self._load_task_example()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _load_task_example(self) -> AgentTaskEnvelope:
        path = REPO_ROOT / 'docs' / 'examples' / 'research-runtime-input.minimal.json'
        with path.open('r', encoding='utf-8-sig') as handle:
            return AgentTaskEnvelope.model_validate(json.load(handle))

    def test_run_task_updates_ledger_and_returns_structured_result_in_mock_mode(self) -> None:
        service = ResearchRuntimeService(repository=self.repository, runtime_mode='mock')
        result = service.run_task(self.task)
        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.status, 'completed')
        self.assertGreaterEqual(len(result.findings), 1)

        ledger = service.get_ledger('ledger-session-phase2-001')
        self.assertIsNotNone(ledger)
        self.assertGreaterEqual(len(ledger.task_history), 1)
        self.assertGreaterEqual(len(ledger.evidence_log), 1)
        self.assertGreaterEqual(len(ledger.final_artifacts), 1)

    def test_run_task_uses_agents_sdk_runtime_when_enabled(self) -> None:
        expected_result = AgentResult(
            contract_version='1.0',
            task_id=self.task.task_id,
            produced_by='manager',
            status='completed',
            summary='Agents SDK runtime completed the research workflow.',
            findings=[],
            completed_at=self.task.created_at,
        )
        service = ResearchRuntimeService(
            repository=self.repository,
            runtime_mode='agents_sdk',
            sdk_runtime=_FakeSDKRuntime(available=True, result=expected_result),
        )

        result = service.run_task(self.task)
        self.assertEqual(result.summary, expected_result.summary)

        ledger = service.get_ledger('ledger-session-phase2-001')
        self.assertIsNotNone(ledger)
        self.assertGreaterEqual(len(ledger.task_history), 1)
        self.assertIn('runtime mode: agents_sdk', ledger.synthesis_notes)

    def test_run_task_falls_back_to_mock_when_sdk_runtime_is_unavailable(self) -> None:
        service = ResearchRuntimeService(
            repository=self.repository,
            runtime_mode='agents_sdk',
            sdk_runtime=_FakeSDKRuntime(available=False),
        )

        result = service.run_task(self.task)
        self.assertEqual(result.status, 'completed')
        self.assertIn('fell back to mock mode', result.follow_up_items[0])


if __name__ == '__main__':
    unittest.main()
