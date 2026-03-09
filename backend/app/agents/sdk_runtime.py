from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from app.agents.agent_factory import AGENTS_SDK_AVAILABLE, ResearchAgentFactory
from app.agents.manager import ManagerAgentOutput, ResearchResultAssembler
from app.agents.run_state import mark_review_required, record_output, transition_state
from app.agents.runtime_tools import ResearchAgentContext, resolve_session_db_path
from app.schemas.research_runtime import AgentResult, AgentTaskEnvelope, ResearchLedger

try:
    from agents import (
        Runner,
        gen_trace_id,
        set_default_openai_api,
        set_default_openai_client,
        set_default_openai_key,
        set_tracing_disabled,
    )
    from openai import AsyncOpenAI
except ImportError:
    Runner = None
    gen_trace_id = None
    set_default_openai_api = None
    set_default_openai_client = None
    set_default_openai_key = None
    set_tracing_disabled = None
    AsyncOpenAI = None


logger = logging.getLogger("uvicorn.error")


class AgentsSDKResearchRuntime:
    def __init__(
        self,
        *,
        model: str,
        openai_api_key: str | None,
        openai_base_url: str | None = None,
        tracing_enabled: bool,
        session_db_path: str | None = None,
        assembler: ResearchResultAssembler | None = None,
    ):
        self.model = model
        self.openai_api_key = openai_api_key or None
        self.openai_base_url = openai_base_url or None
        self.tracing_enabled = tracing_enabled
        self.session_db_path = resolve_session_db_path(session_db_path)
        self.assembler = assembler or ResearchResultAssembler()

    def is_available(self) -> bool:
        return AGENTS_SDK_AVAILABLE and Runner is not None and bool(self.openai_api_key)

    def run(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> tuple[AgentResult, ResearchLedger]:
        if not AGENTS_SDK_AVAILABLE or Runner is None:
            raise RuntimeError("openai-agents is not installed")
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        runtime_started_at = perf_counter()
        logger.info(
            "[research-runtime] agents_sdk runtime start task_id=%s ledger_id=%s model=%s base_url=%s tracing=%s session_db=%s",
            task.task_id,
            ledger.ledger_id,
            self.model,
            self.openai_base_url,
            self.tracing_enabled,
            self.session_db_path,
        )
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
            base_url=self.openai_base_url,
        )
        context.session_ids["manager"] = f"{task.session_id}-manager"
        if manager_trace_id:
            context.trace_ids["manager"] = manager_trace_id

        transition_state(
            ledger,
            "retrieving_local_context",
            actor="agents-sdk",
            message="Preparing Ark-compatible agent context and local tools.",
        )
        transition_state(
            ledger,
            "reasoning",
            actor="agents-sdk",
            message="Running manager and specialist agents.",
        )

        manager_started_at = perf_counter()
        logger.info(
            "[research-runtime] agents_sdk manager step start task_id=%s session_id=%s",
            task.task_id,
            context.session_ids["manager"],
        )
        manager_output = factory.run_manager(context, self._build_manager_input(task, ledger))
        logger.info(
            "[research-runtime] agents_sdk manager step completed task_id=%s summary_chars=%s blockers=%s follow_up_items=%s elapsed_ms=%.2f",
            task.task_id,
            len(manager_output.summary),
            len(manager_output.blockers),
            len(manager_output.follow_up_items),
            (perf_counter() - manager_started_at) * 1000,
        )

        specialists_started_at = perf_counter()
        pipeline = factory.ensure_specialist_outputs(context)
        logger.info(
            "[research-runtime] agents_sdk specialist pipeline completed task_id=%s flow=%s elapsed_ms=%.2f",
            task.task_id,
            pipeline.get("flow"),
            (perf_counter() - specialists_started_at) * 1000,
        )
        transition_state(
            ledger,
            "validating_output",
            actor="agents-sdk",
            message="Recording validated Ark runtime outputs.",
        )

        completed_at = datetime.now(timezone.utc)
        runtime_metadata = factory.build_runtime_metadata(context)
        if task.task_type in {
            "competition_recommendation",
            "competition_eligibility_check",
            "competition_timeline_plan",
        }:
            specialist_name = str(pipeline["specialist_name"])
            validated_output = context.specialist_outputs[specialist_name]
            record_output(
                ledger,
                stage="final",
                payload=validated_output.model_dump(mode="json", exclude_none=True),
                repaired=True,
            )
            review_message = context.review_flags.get(specialist_name) or context.review_flags.get("manager")
            review_required = bool(review_message)
            result, updated_ledger = self.assembler.apply_competition_output(
                task=task,
                ledger=ledger,
                specialist_name=specialist_name,
                validated_output=validated_output,
                started_at=started_at,
                completed_at=completed_at,
                runtime_label="agents_sdk",
                review_required=review_required,
                review_message=review_message,
                follow_up_items=manager_output.follow_up_items,
                blockers=manager_output.blockers,
                runtime_metadata=runtime_metadata,
            )
            if review_required:
                mark_review_required(
                    updated_ledger,
                    actor="agents-sdk",
                    message=review_message or "Ark runtime output requires manual review.",
                )
        else:
            record_output(ledger, stage="legacy_pipeline", payload=pipeline, repaired=True)
            result, updated_ledger = self.assembler.apply_pipeline(
                task=task,
                ledger=ledger,
                pipeline=pipeline,
                started_at=started_at,
                completed_at=completed_at,
                runtime_label="agents_sdk",
                summary=manager_output.summary,
                follow_up_items=manager_output.follow_up_items,
                blockers=manager_output.blockers,
                runtime_metadata=runtime_metadata,
            )

        logger.info(
            "[research-runtime] agents_sdk runtime completed task_id=%s ledger_id=%s status=%s artifacts=%s findings=%s elapsed_ms=%.2f",
            task.task_id,
            updated_ledger.ledger_id,
            result.status,
            len(result.artifacts),
            len(result.findings),
            (perf_counter() - runtime_started_at) * 1000,
        )
        return result, updated_ledger

    def _configure_sdk(self) -> None:
        logger.info(
            "[research-runtime] configuring Ark chat_completions client base_url=%s tracing=%s session_db=%s",
            self.openai_base_url,
            self.tracing_enabled,
            self.session_db_path,
        )
        custom_client = AsyncOpenAI(
            api_key=self.openai_api_key,
            base_url=self.openai_base_url,
        )
        set_default_openai_client(custom_client, use_for_tracing=False)
        set_default_openai_api("chat_completions")
        set_default_openai_key(self.openai_api_key, use_for_tracing=False)
        set_tracing_disabled(not self.tracing_enabled)

    def _build_manager_input(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> str:
        payload: dict[str, Any] = {
            "task_id": task.task_id,
            "session_id": task.session_id,
            "ledger_id": ledger.ledger_id,
            "task_type": task.task_type,
            "topic": ledger.topic,
            "research_question": ledger.research_question,
            "objective": task.objective,
            "payload": task.payload,
            "constraints": task.constraints,
            "expected_output": task.expected_output.model_dump(mode="json") if task.expected_output else None,
        }
        return json.dumps(payload, ensure_ascii=False)
