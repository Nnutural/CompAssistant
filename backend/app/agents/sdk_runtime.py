from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.agents.agent_factory import AGENTS_SDK_AVAILABLE, ResearchAgentFactory
from app.agents.manager import ManagerAgentOutput, ResearchResultAssembler
from app.agents.runtime_tools import ResearchAgentContext, resolve_session_db_path
from app.schemas.research_runtime import AgentResult, AgentTaskEnvelope, ResearchLedger

try:
    from agents import Runner, gen_trace_id, set_default_openai_api, set_default_openai_key
except ImportError:
    Runner = None
    gen_trace_id = None
    set_default_openai_api = None
    set_default_openai_key = None


class AgentsSDKResearchRuntime:
    def __init__(
        self,
        *,
        model: str,
        openai_api_key: str | None,
        tracing_enabled: bool,
        session_db_path: str | None = None,
        assembler: ResearchResultAssembler | None = None,
    ):
        self.model = model
        self.openai_api_key = openai_api_key or None
        self.tracing_enabled = tracing_enabled
        self.session_db_path = resolve_session_db_path(session_db_path)
        self.assembler = assembler or ResearchResultAssembler()

    def is_available(self) -> bool:
        return AGENTS_SDK_AVAILABLE and Runner is not None and bool(self.openai_api_key)

    def run(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> tuple[AgentResult, ResearchLedger]:
        if not AGENTS_SDK_AVAILABLE or Runner is None:
            raise RuntimeError('openai-agents is not installed')
        if not self.openai_api_key:
            raise RuntimeError('OPENAI_API_KEY is not configured')

        self._configure_sdk()
        started_at = datetime.now(timezone.utc)
        manager_trace_id = gen_trace_id() if self.tracing_enabled and gen_trace_id is not None else None
        context = ResearchAgentContext(
            task=task,
            ledger=ledger,
            model=self.model,
            session_db_path=self.session_db_path,
            tracing_enabled=self.tracing_enabled,
            trace_group_id=task.session_id,
            manager_trace_id=manager_trace_id,
        )

        factory = ResearchAgentFactory(
            model=self.model,
            session_db_path=self.session_db_path,
            tracing_enabled=self.tracing_enabled,
        )
        manager_agent = factory.build_manager_agent()
        context.session_ids['manager'] = f'{task.session_id}-manager'
        if manager_trace_id:
            context.trace_ids['manager'] = manager_trace_id

        result = Runner.run_sync(
            manager_agent,
            input=self._build_manager_input(task, ledger),
            context=context,
            session=factory.create_session(context.session_ids['manager']),
            run_config=factory.create_run_config(
                workflow_name='Research Runtime / manager',
                trace_id=manager_trace_id,
                group_id=context.trace_group_id,
            ),
        )
        manager_output = result.final_output_as(ManagerAgentOutput, raise_if_incorrect_type=True)

        pipeline = factory.ensure_specialist_outputs(context)
        completed_at = datetime.now(timezone.utc)
        return self.assembler.apply_pipeline(
            task=task,
            ledger=ledger,
            pipeline=pipeline,
            started_at=started_at,
            completed_at=completed_at,
            runtime_label='agents_sdk',
            summary=manager_output.summary,
            follow_up_items=manager_output.follow_up_items,
            blockers=manager_output.blockers,
            runtime_metadata=factory.build_runtime_metadata(context),
        )

    def _configure_sdk(self) -> None:
        set_default_openai_api('responses')
        set_default_openai_key(self.openai_api_key, use_for_tracing=self.tracing_enabled)

    def _build_manager_input(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> str:
        payload: dict[str, Any] = {
            'task_id': task.task_id,
            'session_id': task.session_id,
            'ledger_id': ledger.ledger_id,
            'topic': ledger.topic,
            'research_question': ledger.research_question,
            'objective': task.objective,
            'payload': task.payload,
            'constraints': task.constraints,
            'expected_output': task.expected_output.model_dump(mode='json') if task.expected_output else None,
        }
        return json.dumps(payload, ensure_ascii=False)
