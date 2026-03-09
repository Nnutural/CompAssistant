import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.critic import CriticOutput  # noqa: E402
from app.agents.evidence_scout import EvidenceScoutOutput  # noqa: E402
from app.agents.manager import ManagerAgentOutput  # noqa: E402
from app.agents.sdk_runtime import AgentsSDKResearchRuntime  # noqa: E402
from app.agents.trend_scout import TrendScoutOutput  # noqa: E402
from app.schemas.research_runtime import AgentTaskEnvelope, EvidenceRecord, FindingItem, ResearchLedger, SourceRecord  # noqa: E402


class _FakeRunResult:
    def __init__(self, final_output):
        self.final_output = final_output

    def final_output_as(self, cls, raise_if_incorrect_type: bool = False):
        if raise_if_incorrect_type and not isinstance(self.final_output, cls):
            raise TypeError(f'Expected {cls}, got {type(self.final_output)}')
        return self.final_output


class AgentsSDKResearchRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.task = self._load_model('research-runtime-input.minimal.json', AgentTaskEnvelope)
        self.ledger = self._load_model('research-ledger.minimal.json', ResearchLedger)
        self.runtime = AgentsSDKResearchRuntime(
            model='deepseek-v3-2-251201',
            openai_api_key='test-key',
            openai_base_url='https://ark.cn-beijing.volces.com/api/v3',
            tracing_enabled=False,
            session_db_path=str(Path(self.temp_dir.name) / 'sessions.sqlite3'),
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _load_model(self, filename: str, model_cls):
        path = REPO_ROOT / 'docs' / 'examples' / filename
        with path.open('r', encoding='utf-8-sig') as handle:
            return model_cls.model_validate(json.load(handle))

    @patch('app.agents.sdk_runtime.AsyncOpenAI')
    @patch('app.agents.sdk_runtime.set_default_openai_client')
    @patch('app.agents.sdk_runtime.set_tracing_disabled')
    @patch('app.agents.sdk_runtime.set_default_openai_key')
    @patch('app.agents.sdk_runtime.set_default_openai_api')
    @patch('app.agents.agent_factory.Runner.run_sync')
    def test_sdk_runtime_runs_with_patched_runner(
        self,
        run_sync_mock,
        set_api_mock,
        set_key_mock,
        set_tracing_disabled_mock,
        set_client_mock,
        async_client_cls,
    ) -> None:
        def side_effect(agent, input, **kwargs):
            if agent.name == 'research-manager':
                return _FakeRunResult(
                    ManagerAgentOutput(
                        summary='Agents SDK runtime completed the research workflow.',
                        follow_up_items=['Keep Ark-compatible chat completions as the default real runtime path.'],
                        blockers=[],
                    )
                )
            if agent.name == 'trend-scout':
                return _FakeRunResult(
                    TrendScoutOutput(
                        directions=[
                            'AI for scientific workflows system design patterns',
                            'AI for scientific workflows evidence collection workflow',
                            'AI for scientific workflows evaluation and risk controls',
                        ],
                        notes=['TrendScout returned deterministic structured directions.'],
                    )
                )
            if agent.name == 'evidence-scout':
                return _FakeRunResult(
                    EvidenceScoutOutput(
                        sources=[
                            SourceRecord(
                                source_id='task-phase2-001-source-1',
                                source_type='note',
                                title='AI for scientific workflows system design patterns seed note',
                                locator='mock://research-runtime/task-phase2-001/source/1',
                                credibility='medium',
                                captured_by='evidence-scout',
                                tags=['offline', 'local-tool', 'phase3'],
                            )
                        ],
                        evidence=[
                            EvidenceRecord(
                                evidence_id='task-phase2-001-evidence-1-1',
                                source_id='task-phase2-001-source-1',
                                claim='Stable contracts make the runtime easier to test.',
                                excerpt='Deterministic local evidence supports repeatable tests.',
                                captured_by='evidence-scout',
                                related_task_id='task-phase2-001',
                            )
                        ],
                        notes=['EvidenceScout returned deterministic local evidence.'],
                    )
                )
            if agent.name == 'critic':
                return _FakeRunResult(
                    CriticOutput(
                        assessment={
                            'novelty': 'The workflow ties contracts, runtime, and ledger updates together.',
                            'feasibility': 'The runtime stays lightweight and testable.',
                            'risk': 'The runtime still lacks network-backed evidence tools.',
                        },
                        findings=[
                            FindingItem(
                                finding_id='task-phase2-001-finding-1',
                                claim='The Ark-only Agents SDK runtime can preserve the existing contract layer.',
                                evidence_refs=['task-phase2-001-evidence-1-1'],
                                confidence='high',
                            )
                        ],
                        notes=['Critic returned a structured assessment.'],
                    )
                )
            raise AssertionError(f'Unexpected agent: {agent.name}')

        run_sync_mock.side_effect = side_effect

        result, updated_ledger = self.runtime.run(self.task, self.ledger)

        self.assertEqual(result.status, 'completed')
        self.assertEqual(result.summary, 'Agents SDK runtime completed the research workflow.')
        self.assertGreaterEqual(len(updated_ledger.task_history), 1)
        self.assertGreaterEqual(len(updated_ledger.evidence_log), 1)
        self.assertIn('runtime mode: agents_sdk', updated_ledger.synthesis_notes)
        self.assertIn('runtime base url: https://ark.cn-beijing.volces.com/api/v3', updated_ledger.synthesis_notes)
        self.assertIn('tracing enabled: false', updated_ledger.synthesis_notes)
        self.assertIn('used mock fallback: false', updated_ledger.synthesis_notes)
        set_api_mock.assert_called_once_with('chat_completions')
        set_key_mock.assert_called_once_with('test-key', use_for_tracing=False)
        set_tracing_disabled_mock.assert_called_once_with(True)
        async_client_cls.assert_called_once_with(
            api_key='test-key',
            base_url='https://ark.cn-beijing.volces.com/api/v3',
        )
        set_client_mock.assert_called_once_with(async_client_cls.return_value, use_for_tracing=False)

    @patch('app.agents.sdk_runtime.AsyncOpenAI')
    @patch('app.agents.sdk_runtime.set_default_openai_client')
    @patch('app.agents.sdk_runtime.set_tracing_disabled')
    @patch('app.agents.sdk_runtime.set_default_openai_key')
    @patch('app.agents.sdk_runtime.set_default_openai_api')
    @patch('app.agents.agent_factory.Runner.run_sync')
    def test_sdk_runtime_downgrades_to_plain_json_when_structured_output_fails(
        self,
        run_sync_mock,
        set_api_mock,
        set_key_mock,
        set_tracing_disabled_mock,
        set_client_mock,
        async_client_cls,
    ) -> None:
        def side_effect(agent, input, **kwargs):
            is_structured = getattr(agent, 'output_type', None) is not None
            if agent.name == 'research-manager':
                if is_structured:
                    raise RuntimeError('Structured output is unsupported for this Ark model.')
                return _FakeRunResult(
                    json.dumps(
                        {
                            'summary': 'Manager JSON fallback completed the Ark workflow.',
                            'follow_up_items': ['Structured output was downgraded to plain JSON.'],
                            'blockers': [],
                        },
                        ensure_ascii=False,
                    )
                )
            if agent.name == 'trend-scout':
                if is_structured:
                    raise RuntimeError('Structured output is unsupported for this Ark model.')
                return _FakeRunResult(
                    json.dumps(
                        {
                            'agent': 'trend-scout',
                            'directions': [
                                'AI for scientific workflows system design patterns',
                                'AI for scientific workflows evidence collection workflow',
                            ],
                            'notes': ['TrendScout JSON fallback succeeded.'],
                        },
                        ensure_ascii=False,
                    )
                )
            if agent.name == 'evidence-scout':
                if is_structured:
                    raise RuntimeError('Structured output is unsupported for this Ark model.')
                return _FakeRunResult(
                    json.dumps(
                        {
                            'agent': 'evidence-scout',
                            'sources': [
                                {
                                    'source_id': 'task-phase2-001-source-1',
                                    'source_type': 'note',
                                    'title': 'AI for scientific workflows system design patterns seed note',
                                    'locator': 'mock://research-runtime/task-phase2-001/source/1',
                                    'credibility': 'medium',
                                    'captured_by': 'evidence-scout',
                                    'tags': ['offline', 'local-tool', 'phase3'],
                                }
                            ],
                            'evidence': [
                                {
                                    'evidence_id': 'task-phase2-001-evidence-1-1',
                                    'source_id': 'task-phase2-001-source-1',
                                    'claim': 'Stable contracts make the runtime easier to test.',
                                    'excerpt': 'Deterministic local evidence supports repeatable tests.',
                                    'captured_by': 'evidence-scout',
                                    'related_task_id': 'task-phase2-001',
                                }
                            ],
                            'notes': ['EvidenceScout JSON fallback succeeded.'],
                        },
                        ensure_ascii=False,
                    )
                )
            if agent.name == 'critic':
                if is_structured:
                    raise RuntimeError('Structured output is unsupported for this Ark model.')
                return _FakeRunResult(
                    json.dumps(
                        {
                            'agent': 'critic',
                            'assessment': {
                                'novelty': 'JSON fallback kept the runtime usable.',
                                'feasibility': 'Ark chat completions can still drive the tool workflow.',
                                'risk': 'Schema-grade outputs still depend on local validation.',
                            },
                            'findings': [
                                {
                                    'finding_id': 'task-phase2-001-finding-1',
                                    'claim': 'The runtime can recover by validating plain JSON locally.',
                                    'evidence_refs': ['task-phase2-001-evidence-1-1'],
                                    'confidence': 'high',
                                }
                            ],
                            'notes': ['Critic JSON fallback succeeded.'],
                        },
                        ensure_ascii=False,
                    )
                )
            raise AssertionError(f'Unexpected agent: {agent.name}')

        run_sync_mock.side_effect = side_effect

        result, updated_ledger = self.runtime.run(self.task, self.ledger)

        self.assertEqual(result.status, 'completed')
        self.assertEqual(result.summary, 'Manager JSON fallback completed the Ark workflow.')
        self.assertGreaterEqual(len(updated_ledger.task_history), 1)
        self.assertGreaterEqual(len(updated_ledger.evidence_log), 1)
        self.assertIn('runtime mode: agents_sdk', updated_ledger.synthesis_notes)
        self.assertIn('used mock fallback: false', updated_ledger.synthesis_notes)
        set_api_mock.assert_called_once_with('chat_completions')
        set_key_mock.assert_called_once_with('test-key', use_for_tracing=False)
        set_tracing_disabled_mock.assert_called_once_with(True)
        async_client_cls.assert_called_once_with(
            api_key='test-key',
            base_url='https://ark.cn-beijing.volces.com/api/v3',
        )
        set_client_mock.assert_called_once_with(async_client_cls.return_value, use_for_tracing=False)

    @patch('app.agents.sdk_runtime.AsyncOpenAI')
    @patch('app.agents.sdk_runtime.set_default_openai_client')
    @patch('app.agents.sdk_runtime.set_tracing_disabled')
    @patch('app.agents.sdk_runtime.set_default_openai_key')
    @patch('app.agents.sdk_runtime.set_default_openai_api')
    def test_sdk_runtime_configures_custom_base_url_client(
        self,
        set_api_mock,
        set_key_mock,
        set_tracing_disabled_mock,
        set_client_mock,
        async_client_cls,
    ) -> None:
        runtime = AgentsSDKResearchRuntime(
            model='deepseek-v3-2-251201',
            openai_api_key='test-key',
            openai_base_url='https://ark.cn-beijing.volces.com/api/v3',
            tracing_enabled=False,
            session_db_path=str(Path(self.temp_dir.name) / 'sessions.sqlite3'),
        )

        runtime._configure_sdk()

        set_api_mock.assert_called_once_with('chat_completions')
        set_key_mock.assert_called_once_with('test-key', use_for_tracing=False)
        set_tracing_disabled_mock.assert_called_once_with(True)
        async_client_cls.assert_called_once_with(
            api_key='test-key',
            base_url='https://ark.cn-beijing.volces.com/api/v3',
        )
        set_client_mock.assert_called_once_with(async_client_cls.return_value, use_for_tracing=False)

    @unittest.skipUnless(
        bool(os.getenv('OPENAI_API_KEY')) and os.getenv('RUN_ARK_INTEGRATION') == '1',
        'Set OPENAI_API_KEY and RUN_ARK_INTEGRATION=1 to run the live Ark Agents SDK integration test.',
    )
    def test_live_ark_agents_sdk_integration(self) -> None:
        runtime = AgentsSDKResearchRuntime(
            model=os.getenv('OPENAI_DEFAULT_MODEL', 'deepseek-v3-2-251201'),
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            openai_base_url=os.getenv('OPENAI_BASE_URL', 'https://ark.cn-beijing.volces.com/api/v3'),
            tracing_enabled=False,
            session_db_path=str(Path(self.temp_dir.name) / 'live-sessions.sqlite3'),
        )
        result, updated_ledger = runtime.run(self.task, self.ledger)
        self.assertEqual(result.status, 'completed')
        self.assertGreaterEqual(len(updated_ledger.task_history), 1)


if __name__ == '__main__':
    unittest.main()
