from __future__ import annotations

import json
import logging
import re
from time import perf_counter
from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from app.agents.critic import CriticOutput, build_critic_agent_with_mode
from app.agents.evidence_scout import EvidenceScoutOutput, build_evidence_scout_agent_with_mode
from app.agents.manager import ManagerAgentOutput
from app.agents.runtime_tools import ResearchAgentContext
from app.agents.trend_scout import TrendScoutOutput, build_trend_scout_agent_with_mode

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

TStructuredOutput = TypeVar('TStructuredOutput', bound=BaseModel)
logger = logging.getLogger("uvicorn.error")


class ResearchAgentFactory:
    def __init__(self, *, model: str, session_db_path: str, tracing_enabled: bool, base_url: str | None = None):
        if not AGENTS_SDK_AVAILABLE:
            raise RuntimeError('openai-agents is not installed')
        self.model = model
        self.session_db_path = session_db_path
        self.tracing_enabled = tracing_enabled
        self.base_url = base_url or ''

    def build_manager_agent(self, *, structured: bool = True):
        instructions = (
            'You are the central ResearchManager for an offline-capable research runtime. '
            'The current real runtime only targets Ark-compatible chat completions for minimum viability. '
            'Call run_trend_scout exactly once, then run_evidence_scout exactly once, then run_critic exactly once. '
            'After all three tools have completed, return a concise manager result. '
            'Do not invent network access, external databases, or new contract fields. '
            'Keep the summary short and structured. '
            'If a specialist result is missing, treat that as a blocker.'
        )
        if structured:
            instructions += ' Return only structured output that matches ManagerAgentOutput.'
        else:
            instructions += (
                ' Return only a JSON object with keys: summary, follow_up_items, blockers. '
                'Do not wrap the JSON in markdown fences.'
            )

        return Agent(
            name='research-manager',
            model=self.model,
            tools=[
                self._build_trend_tool(),
                self._build_evidence_tool(),
                self._build_critic_tool(),
            ],
            output_type=ManagerAgentOutput if structured else None,
            instructions=instructions,
        )

    def run_manager(self, context: ResearchAgentContext, input_payload: str) -> ManagerAgentOutput:
        logger.info(
            "[research-runtime] manager agent queued task_id=%s session_id=%s",
            context.task.task_id,
            context.session_ids.get('manager', '<pending>'),
        )
        return self._run_agent_with_output_fallback(
            agent_name='manager',
            build_agent=lambda structured: self.build_manager_agent(structured=structured),
            context=context,
            input_payload=input_payload,
            output_model=ManagerAgentOutput,
        )

    def run_trend_scout(self, context: ResearchAgentContext) -> TrendScoutOutput:
        cached = context.specialist_outputs.get('trend')
        if isinstance(cached, TrendScoutOutput):
            logger.info(
                "[research-runtime] trend-scout using cached output task_id=%s directions=%s",
                context.task.task_id,
                len(cached.directions),
            )
            return cached

        input_payload = json.dumps(
            {
                'task_id': context.task.task_id,
                'ledger_id': context.ledger.ledger_id,
                'topic': context.ledger.topic,
                'objective': context.task.objective,
            },
            ensure_ascii=False,
        )
        output = self._run_agent_with_output_fallback(
            agent_name='trend-scout',
            build_agent=lambda structured: build_trend_scout_agent_with_mode(self.model, structured=structured),
            context=context,
            input_payload=input_payload,
            output_model=TrendScoutOutput,
        )
        logger.info(
            "[research-runtime] trend-scout completed task_id=%s directions=%s notes=%s",
            context.task.task_id,
            len(output.directions),
            len(output.notes),
        )
        context.specialist_outputs['trend'] = output
        return output

    def run_evidence_scout(self, context: ResearchAgentContext) -> EvidenceScoutOutput:
        cached = context.specialist_outputs.get('evidence')
        if isinstance(cached, EvidenceScoutOutput):
            logger.info(
                "[research-runtime] evidence-scout using cached output task_id=%s sources=%s evidence=%s",
                context.task.task_id,
                len(cached.sources),
                len(cached.evidence),
            )
            return cached

        trend_output = self.run_trend_scout(context)
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
        output = self._run_agent_with_output_fallback(
            agent_name='evidence-scout',
            build_agent=lambda structured: build_evidence_scout_agent_with_mode(self.model, structured=structured),
            context=context,
            input_payload=input_payload,
            output_model=EvidenceScoutOutput,
        )
        logger.info(
            "[research-runtime] evidence-scout completed task_id=%s sources=%s evidence=%s notes=%s",
            context.task.task_id,
            len(output.sources),
            len(output.evidence),
            len(output.notes),
        )
        context.specialist_outputs['evidence'] = output
        return output

    def run_critic(self, context: ResearchAgentContext) -> CriticOutput:
        cached = context.specialist_outputs.get('critic')
        if isinstance(cached, CriticOutput):
            logger.info(
                "[research-runtime] critic using cached output task_id=%s findings=%s",
                context.task.task_id,
                len(cached.findings),
            )
            return cached

        trend_output = self.run_trend_scout(context)
        evidence_output = self.run_evidence_scout(context)
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
        output = self._run_agent_with_output_fallback(
            agent_name='critic',
            build_agent=lambda structured: build_critic_agent_with_mode(self.model, structured=structured),
            context=context,
            input_payload=input_payload,
            output_model=CriticOutput,
        )
        logger.info(
            "[research-runtime] critic completed task_id=%s findings=%s notes=%s",
            context.task.task_id,
            len(output.findings),
            len(output.notes),
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

    def build_runtime_metadata(
        self,
        context: ResearchAgentContext,
        *,
        used_mock_fallback: bool = False,
        fallback_reason: str | None = None,
    ) -> dict[str, Any]:
        specialist_sessions = {key: value for key, value in context.session_ids.items() if key != 'manager'}
        specialist_traces = {key: value for key, value in context.trace_ids.items() if key != 'manager'}
        return {
            'mode': 'agents_sdk',
            'model': self.model,
            'base_url': self.base_url,
            'tracing_enabled': self.tracing_enabled,
            'used_mock_fallback': used_mock_fallback,
            'fallback_reason': fallback_reason,
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
            trace_id=trace_id if self.tracing_enabled else None,
            group_id=group_id if self.tracing_enabled else None,
            trace_include_sensitive_data=False,
            trace_metadata={'runtime': 'research-runtime', 'group_id': group_id} if self.tracing_enabled else None,
        )

    def _run_agent_with_output_fallback(
        self,
        *,
        agent_name: str,
        build_agent: Callable[[bool], Any],
        context: ResearchAgentContext,
        input_payload: str,
        output_model: type[TStructuredOutput],
    ) -> TStructuredOutput:
        started_at = perf_counter()
        try:
            logger.info(
                "[research-runtime] %s structured run start task_id=%s",
                agent_name,
                context.task.task_id,
            )
            structured_agent = build_agent(True)
            output = self._run_agent_once(
                agent_name=agent_name,
                agent=structured_agent,
                context=context,
                input_payload=input_payload,
                output_model=output_model,
            )
            logger.info(
                "[research-runtime] %s structured run completed task_id=%s elapsed_ms=%.2f summary=%s",
                agent_name,
                context.task.task_id,
                (perf_counter() - started_at) * 1000,
                self._summarize_output(output),
            )
            return output
        except Exception as structured_error:
            logger.warning(
                "[research-runtime] %s structured run failed task_id=%s error=%s; trying plain JSON fallback",
                agent_name,
                context.task.task_id,
                structured_error,
            )
            plain_json_agent = build_agent(False)
            try:
                plain_output = self._run_agent_once(
                    agent_name=agent_name,
                    agent=plain_json_agent,
                    context=context,
                    input_payload=input_payload,
                    output_model=None,
                )
                output = self._parse_plain_json_output(
                    raw_output=plain_output,
                    output_model=output_model,
                )
                logger.info(
                    "[research-runtime] %s JSON fallback completed task_id=%s elapsed_ms=%.2f summary=%s",
                    agent_name,
                    context.task.task_id,
                    (perf_counter() - started_at) * 1000,
                    self._summarize_output(output),
                )
                return output
            except Exception as fallback_error:
                logger.error(
                    "[research-runtime] %s JSON fallback failed task_id=%s elapsed_ms=%.2f error=%s",
                    agent_name,
                    context.task.task_id,
                    (perf_counter() - started_at) * 1000,
                    fallback_error,
                )
                raise RuntimeError(
                    f'{agent_name} failed in structured mode and JSON fallback mode. '
                    f'structured_error={structured_error}; fallback_error={fallback_error}'
                ) from fallback_error

    def _run_agent_once(
        self,
        *,
        agent_name: str,
        agent,
        context: ResearchAgentContext,
        input_payload: str,
        output_model: type[TStructuredOutput] | None,
    ) -> TStructuredOutput | str:
        session_id = self._get_or_create_session_id(context, agent_name)
        trace_id = self._get_or_create_trace_id(context, agent_name)
        started_at = perf_counter()
        logger.info(
            "[research-runtime] %s runner call start task_id=%s session_id=%s tracing=%s trace_id=%s",
            agent_name,
            context.task.task_id,
            session_id,
            self.tracing_enabled,
            trace_id,
        )
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
        logger.info(
            "[research-runtime] %s runner call completed task_id=%s session_id=%s elapsed_ms=%.2f final_output_type=%s",
            agent_name,
            context.task.task_id,
            session_id,
            (perf_counter() - started_at) * 1000,
            type(result.final_output).__name__,
        )
        if output_model is None:
            final_output = result.final_output
            if isinstance(final_output, str):
                return final_output
            return json.dumps(final_output, ensure_ascii=False)
        return result.final_output_as(output_model, raise_if_incorrect_type=True)

    def _parse_plain_json_output(
        self,
        *,
        raw_output: str,
        output_model: type[TStructuredOutput],
    ) -> TStructuredOutput:
        payload = self._extract_json_payload(raw_output)
        return output_model.model_validate(payload)

    def _extract_json_payload(self, raw_output: str) -> dict[str, Any]:
        text = raw_output.strip()
        fenced_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, flags=re.DOTALL)
        if fenced_match:
            text = fenced_match.group(1).strip()
        if text.startswith('{') and text.endswith('}'):
            return json.loads(text)

        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise ValueError(f'Plain JSON fallback did not return a JSON object: {raw_output}')

    def _summarize_output(self, output: BaseModel | str) -> str:
        if isinstance(output, ManagerAgentOutput):
            return (
                f'summary_chars={len(output.summary)} '
                f'follow_up_items={len(output.follow_up_items)} blockers={len(output.blockers)}'
            )
        if isinstance(output, TrendScoutOutput):
            return f'directions={len(output.directions)} notes={len(output.notes)}'
        if isinstance(output, EvidenceScoutOutput):
            return f'sources={len(output.sources)} evidence={len(output.evidence)} notes={len(output.notes)}'
        if isinstance(output, CriticOutput):
            return f'findings={len(output.findings)} notes={len(output.notes)}'
        if isinstance(output, str):
            return f'text_chars={len(output)}'
        return f'output_type={type(output).__name__}'

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
