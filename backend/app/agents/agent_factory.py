from __future__ import annotations

import json
from typing import Any

from app.agents.critic import CriticOutput, build_critic_agent
from app.agents.evidence_scout import EvidenceScoutOutput, build_evidence_scout_agent
from app.agents.manager import ManagerAgentOutput
from app.agents.runtime_tools import ResearchAgentContext
from app.agents.trend_scout import TrendScoutOutput, build_trend_scout_agent

try:
    from agents import Agent, RunConfig, Runner, function_tool, gen_trace_id
    from agents.memory.sqlite_session import SQLiteSession
    from agents.run_context import RunContextWrapper
except ImportError:
    Agent = None
    RunConfig = None
    Runner = None
    function_tool = None
    gen_trace_id = None
    SQLiteSession = None
    RunContextWrapper = None


AGENTS_SDK_AVAILABLE = all(
    dependency is not None
    for dependency in (Agent, RunConfig, Runner, function_tool, gen_trace_id, SQLiteSession, RunContextWrapper)
)


class ResearchAgentFactory:
    def __init__(self, *, model: str, session_db_path: str, tracing_enabled: bool):
        if not AGENTS_SDK_AVAILABLE:
            raise RuntimeError('openai-agents is not installed')
        self.model = model
        self.session_db_path = session_db_path
        self.tracing_enabled = tracing_enabled

    def build_manager_agent(self):
        return Agent(
            name='research-manager',
            model=self.model,
            tools=[
                self._build_trend_tool(),
                self._build_evidence_tool(),
                self._build_critic_tool(),
            ],
            output_type=ManagerAgentOutput,
            instructions=(
                'You are the central ResearchManager for an offline-capable research runtime. '
                'Call run_trend_scout exactly once, then run_evidence_scout exactly once, then run_critic exactly once. '
                'After all three tools have completed, return a concise ManagerAgentOutput. '
                'Do not invent network access, external databases, or new contract fields. '
                'Keep the summary short and structured. '
                'If a specialist result is missing, treat that as a blocker.'
            ),
        )

    def run_trend_scout(self, context: ResearchAgentContext) -> TrendScoutOutput:
        cached = context.specialist_outputs.get('trend')
        if isinstance(cached, TrendScoutOutput):
            return cached

        agent = build_trend_scout_agent(self.model)
        input_payload = json.dumps(
            {
                'task_id': context.task.task_id,
                'ledger_id': context.ledger.ledger_id,
                'topic': context.ledger.topic,
                'objective': context.task.objective,
            },
            ensure_ascii=False,
        )
        output = self._run_specialist_agent(
            agent_name='trend-scout',
            agent=agent,
            context=context,
            input_payload=input_payload,
            output_model=TrendScoutOutput,
        )
        context.specialist_outputs['trend'] = output
        return output

    def run_evidence_scout(self, context: ResearchAgentContext) -> EvidenceScoutOutput:
        cached = context.specialist_outputs.get('evidence')
        if isinstance(cached, EvidenceScoutOutput):
            return cached

        trend_output = self.run_trend_scout(context)
        agent = build_evidence_scout_agent(self.model)
        input_payload = json.dumps(
            {
                'task_id': context.task.task_id,
                'ledger_id': context.ledger.ledger_id,
                'topic': context.ledger.topic,
                'objective': context.task.objective,
                'directions': trend_output.directions,
            },
            ensure_ascii=False,
        )
        output = self._run_specialist_agent(
            agent_name='evidence-scout',
            agent=agent,
            context=context,
            input_payload=input_payload,
            output_model=EvidenceScoutOutput,
        )
        context.specialist_outputs['evidence'] = output
        return output

    def run_critic(self, context: ResearchAgentContext) -> CriticOutput:
        cached = context.specialist_outputs.get('critic')
        if isinstance(cached, CriticOutput):
            return cached

        trend_output = self.run_trend_scout(context)
        evidence_output = self.run_evidence_scout(context)
        agent = build_critic_agent(self.model)
        input_payload = json.dumps(
            {
                'task_id': context.task.task_id,
                'ledger_id': context.ledger.ledger_id,
                'topic': context.ledger.topic,
                'objective': context.task.objective,
                'direction_count': len(trend_output.directions),
                'evidence_ids': [item.evidence_id for item in evidence_output.evidence],
                'evidence_claims': [item.claim for item in evidence_output.evidence[:3]],
            },
            ensure_ascii=False,
        )
        output = self._run_specialist_agent(
            agent_name='critic',
            agent=agent,
            context=context,
            input_payload=input_payload,
            output_model=CriticOutput,
        )
        context.specialist_outputs['critic'] = output
        return output

    def ensure_specialist_outputs(self, context: ResearchAgentContext) -> dict[str, Any]:
        trend = self.run_trend_scout(context)
        evidence = self.run_evidence_scout(context)
        critic = self.run_critic(context)
        return {
            'trend': trend.model_dump(mode='json'),
            'evidence': evidence.model_dump(mode='json'),
            'critic': critic.model_dump(mode='json'),
        }

    def build_runtime_metadata(self, context: ResearchAgentContext) -> dict[str, Any]:
        specialist_sessions = {key: value for key, value in context.session_ids.items() if key != 'manager'}
        specialist_traces = {key: value for key, value in context.trace_ids.items() if key != 'manager'}
        return {
            'mode': 'agents_sdk',
            'manager_session_id': context.session_ids.get('manager'),
            'manager_trace_id': context.trace_ids.get('manager') or context.manager_trace_id,
            'specialist_session_ids': specialist_sessions,
            'specialist_trace_ids': specialist_traces,
        }

    def create_session(self, session_id: str):
        return SQLiteSession(session_id=session_id, db_path=self.session_db_path)

    def create_run_config(self, *, workflow_name: str, trace_id: str | None, group_id: str):
        return RunConfig(
            model=self.model,
            tracing_disabled=not self.tracing_enabled,
            workflow_name=workflow_name,
            trace_id=trace_id,
            group_id=group_id,
            trace_include_sensitive_data=False,
            trace_metadata={'runtime': 'research-runtime', 'group_id': group_id},
        )

    def _run_specialist_agent(self, *, agent_name: str, agent, context: ResearchAgentContext, input_payload: str, output_model):
        session_id = self._get_or_create_session_id(context, agent_name)
        trace_id = self._get_or_create_trace_id(context, agent_name)
        result = Runner.run_sync(
            agent,
            input=input_payload,
            context=context,
            session=self.create_session(session_id),
            run_config=self.create_run_config(
                workflow_name=f'Research Runtime / {agent_name}',
                trace_id=trace_id,
                group_id=context.trace_group_id,
            ),
        )
        return result.final_output_as(output_model, raise_if_incorrect_type=True)

    def _build_trend_tool(self):
        @function_tool(
            name_override='run_trend_scout',
            description_override='Run the TrendScout specialist agent and cache its structured output.',
        )
        def run_trend_scout_tool(ctx: RunContextWrapper[ResearchAgentContext]) -> dict[str, Any]:
            output = self.run_trend_scout(ctx.context)
            return output.model_dump(mode='json')

        return run_trend_scout_tool

    def _build_evidence_tool(self):
        @function_tool(
            name_override='run_evidence_scout',
            description_override='Run the EvidenceScout specialist agent using the current trend output.',
        )
        def run_evidence_scout_tool(ctx: RunContextWrapper[ResearchAgentContext]) -> dict[str, Any]:
            output = self.run_evidence_scout(ctx.context)
            return output.model_dump(mode='json')

        return run_evidence_scout_tool

    def _build_critic_tool(self):
        @function_tool(
            name_override='run_critic',
            description_override='Run the Critic specialist agent using the cached trend and evidence outputs.',
        )
        def run_critic_tool(ctx: RunContextWrapper[ResearchAgentContext]) -> dict[str, Any]:
            output = self.run_critic(ctx.context)
            return output.model_dump(mode='json')

        return run_critic_tool

    def _get_or_create_session_id(self, context: ResearchAgentContext, agent_name: str) -> str:
        if agent_name not in context.session_ids:
            context.session_ids[agent_name] = f'{context.task.session_id}-{agent_name}'
        return context.session_ids[agent_name]

    def _get_or_create_trace_id(self, context: ResearchAgentContext, agent_name: str) -> str | None:
        if not self.tracing_enabled:
            return None
        if agent_name not in context.trace_ids:
            context.trace_ids[agent_name] = gen_trace_id()
        return context.trace_ids[agent_name]
