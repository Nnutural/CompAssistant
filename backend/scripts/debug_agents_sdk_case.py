from __future__ import annotations

import argparse
import json
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.agent_factory import ResearchAgentFactory  # noqa: E402
from app.agents.competition_recommender import build_competition_recommender_agent_with_mode  # noqa: E402
from app.agents.manager import process_output_stage  # noqa: E402
from app.agents.runtime_tools import ResearchAgentContext, build_recommendation_tools  # noqa: E402
from app.repositories.ledger_repository import LedgerRepository  # noqa: E402
from app.schemas.agent_tasks import AgentTaskCreateRequest  # noqa: E402
from app.schemas.research_runtime import AgentTaskEnvelope, CompetitionRecommendationArtifact  # noqa: E402
from app.services.evaluation_service import load_evaluation_cases  # noqa: E402
from app.services.research_runtime_service import ResearchRuntimeService  # noqa: E402

try:
    from agents import RunHooks, Runner, gen_trace_id
except ImportError:  # pragma: no cover
    RunHooks = object  # type: ignore[assignment]
    Runner = None
    gen_trace_id = None


def _preview(value: Any, *, limit: int = 240) -> str:
    text = str(value).replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


class DebugRunHooks(RunHooks[ResearchAgentContext]):  # type: ignore[misc]
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def _record(self, event_type: str, **payload: Any) -> None:
        self.events.append(
            {
                "event": event_type,
                "at": datetime.now(timezone.utc).isoformat(),
                **payload,
            }
        )

    async def on_agent_start(self, context, agent) -> None:
        self._record("agent_start", agent=getattr(agent, "name", type(agent).__name__))

    async def on_agent_end(self, context, agent, output) -> None:
        self._record(
            "agent_end",
            agent=getattr(agent, "name", type(agent).__name__),
            output_type=type(output).__name__,
        )

    async def on_llm_start(self, context, agent, system_prompt, input_items) -> None:
        self._record(
            "llm_start",
            agent=getattr(agent, "name", type(agent).__name__),
            system_prompt_preview=_preview(system_prompt or ""),
            input_item_count=len(input_items or []),
        )

    async def on_llm_end(self, context, agent, response) -> None:
        output_items = getattr(response, "output", None)
        self._record(
            "llm_end",
            agent=getattr(agent, "name", type(agent).__name__),
            response_id=getattr(response, "id", None),
            output_item_count=len(output_items) if isinstance(output_items, list) else None,
        )

    async def on_tool_start(self, context, agent, tool) -> None:
        self._record(
            "tool_start",
            agent=getattr(agent, "name", type(agent).__name__),
            tool=getattr(tool, "name", type(tool).__name__),
        )

    async def on_tool_end(self, context, agent, tool, result) -> None:
        self._record(
            "tool_end",
            agent=getattr(agent, "name", type(agent).__name__),
            tool=getattr(tool, "name", type(tool).__name__),
            result_preview=_preview(result),
        )

    async def on_handoff(self, context, from_agent, to_agent) -> None:
        self._record(
            "handoff",
            from_agent=getattr(from_agent, "name", type(from_agent).__name__),
            to_agent=getattr(to_agent, "name", type(to_agent).__name__),
        )


def _build_task(case_id: str) -> AgentTaskEnvelope:
    case = next(case for case in load_evaluation_cases("competition_recommendation") if case.id == case_id)
    request = AgentTaskCreateRequest.model_validate(
        {
            "task_type": case.task_type,
            "objective": case.input.get("objective") or "为当前用户画像生成竞赛推荐。",
            "payload": case.input.get("payload", {}),
            "task_id": f"debug-{case.id}",
            "session_id": f"debug-{case.id}",
            "dry_run": False,
        }
    )
    return AgentTaskEnvelope(
        contract_version="1.0",
        task_id=request.task_id or f"debug-{case.id}",
        session_id=request.session_id or f"debug-{case.id}",
        task_type=request.task_type,
        requested_by=request.requested_by,
        priority=request.priority,
        objective=request.objective or "为当前用户画像生成竞赛推荐。",
        payload=request.payload,
        constraints=request.constraints,
        dry_run=request.dry_run,
        created_at=datetime.now(timezone.utc),
    )


def _build_input_payload(task: AgentTaskEnvelope, ledger_id: str) -> str:
    return json.dumps(
        {
            "task_id": task.task_id,
            "ledger_id": ledger_id,
            "objective": task.objective,
            "profile": task.payload.get("profile") or task.payload.get("user_profile") or {},
        },
        ensure_ascii=False,
    )


def _classify_root_cause(path_label: str, error: Exception, events: list[dict[str, Any]]) -> str:
    message = str(error).lower()
    tool_starts = [event for event in events if event.get("event") == "tool_start"]
    llm_starts = [event for event in events if event.get("event") == "llm_start"]
    repeated_tool = len(tool_starts) > 1
    if "max turns" in message:
        if repeated_tool:
            return f"{path_label}: tool loop or repeated grounding exhausted the turn budget"
        if len(llm_starts) > 1:
            return f"{path_label}: repeated self-repair / response retries exhausted the turn budget"
        return f"{path_label}: turn budget exhausted before the model produced a final artifact"
    if "timed out" in message:
        if repeated_tool:
            return f"{path_label}: provider call stayed active after tool grounding and hit the runner timeout"
        return f"{path_label}: provider response or post-processing exceeded the runner timeout"
    return f"{path_label}: {type(error).__name__}: {error}"


def _run_provider_path(
    *,
    factory: ResearchAgentFactory,
    context: ResearchAgentContext,
    task: AgentTaskEnvelope,
    structured: bool,
) -> dict[str, Any]:
    if Runner is None:
        raise RuntimeError("openai-agents is not installed")
    path_label = "structured" if structured else "plain_json_fallback"
    agent = build_competition_recommender_agent_with_mode(
        factory.model,
        structured=structured,
        tools=build_recommendation_tools(),
    )
    budget = factory.get_run_budget(agent_name="competition-recommender", path_label=path_label)
    hooks = DebugRunHooks()
    session_id = f"{task.session_id}-competition-recommender-{path_label}"
    context.session_ids["competition-recommender"] = session_id
    if factory.tracing_enabled and gen_trace_id is not None:
        context.trace_ids["competition-recommender"] = gen_trace_id()
    input_payload = _build_input_payload(task, context.ledger.ledger_id)

    def _invoke_runner():
        return Runner.run_sync(
            agent,
            input=input_payload,
            context=context,
            max_turns=budget.max_turns,
            hooks=hooks,
            session=factory.create_session(session_id),
            run_config=factory.create_run_config(
                workflow_name=f"Debug / {path_label}",
                trace_id=context.trace_ids.get("competition-recommender"),
                group_id=context.trace_group_id,
            ),
        )

    try:
        if budget.timeout_seconds > 0:
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"debug-{path_label}") as executor:
                future = executor.submit(_invoke_runner)
                try:
                    result = future.result(timeout=budget.timeout_seconds)
                except FutureTimeoutError as exc:
                    future.cancel()
                    raise TimeoutError(f"Runner call timed out after {budget.timeout_seconds:.1f}s") from exc
        else:
            result = _invoke_runner()

        validated_output, review_required, review_message = process_output_stage(
            ledger=context.ledger,
            stage=f"competition-recommender:{path_label}",
            raw_output=result.final_output,
            output_model=CompetitionRecommendationArtifact,
            agent_name="competition-recommender",
        )
        return {
            "path_label": path_label,
            "ok": True,
            "budget": {
                "max_turns": budget.max_turns,
                "timeout_seconds": budget.timeout_seconds,
                "input_chars": len(input_payload),
            },
            "prompt_summary": {
                "instructions_preview": _preview(getattr(agent, "instructions", "")),
                "instructions_chars": len(str(getattr(agent, "instructions", ""))),
            },
            "schema_summary": {
                "output_type": type(getattr(agent, "output_type", None)).__name__,
                "tool_names": [getattr(tool, "name", type(tool).__name__) for tool in getattr(agent, "tools", []) or []],
            },
            "turn_summary": {
                "llm_turns": sum(1 for event in hooks.events if event["event"] == "llm_start"),
                "tool_calls": sum(1 for event in hooks.events if event["event"] == "tool_start"),
                "events": hooks.events,
            },
            "artifact_validation_ok": True,
            "review_required": review_required,
            "review_message": review_message,
            "artifact_summary": {
                "recommendation_count": len(validated_output.recommendations),
                "risk_overview_count": len(validated_output.risk_overview),
            },
        }
    except Exception as exc:
        return {
            "path_label": path_label,
            "ok": False,
            "budget": {
                "max_turns": budget.max_turns,
                "timeout_seconds": budget.timeout_seconds,
                "input_chars": len(input_payload),
            },
            "prompt_summary": {
                "instructions_preview": _preview(getattr(agent, "instructions", "")),
                "instructions_chars": len(str(getattr(agent, "instructions", ""))),
            },
            "schema_summary": {
                "output_type": type(getattr(agent, "output_type", None)).__name__,
                "tool_names": [getattr(tool, "name", type(tool).__name__) for tool in getattr(agent, "tools", []) or []],
            },
            "turn_summary": {
                "llm_turns": sum(1 for event in hooks.events if event["event"] == "llm_start"),
                "tool_calls": sum(1 for event in hooks.events if event["event"] == "tool_start"),
                "events": hooks.events,
            },
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "root_cause": _classify_root_cause(path_label, exc, hooks.events),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug a single agents_sdk case without mock fallback.")
    parser.add_argument("--case-id", default="recommendation-003", help="Evaluation case id to reproduce.")
    parser.add_argument(
        "--path",
        choices=["structured", "plain_json_fallback", "both"],
        default="both",
        help="Which provider path to run.",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON output.")
    args = parser.parse_args()

    task = _build_task(args.case_id)
    with tempfile.TemporaryDirectory() as temp_dir:
        service = ResearchRuntimeService(
            repository=LedgerRepository(temp_dir),
            runtime_mode="agents_sdk",
            strict_mode=True,
        )
        try:
            runtime = service._get_sdk_runtime()
            runtime._configure_sdk()
            ledger = service._load_or_create_ledger(task)
            service._prepare_run(ledger, task, reset_tracking=True)
            context = ResearchAgentContext(
                task=task,
                ledger=ledger,
                model=runtime.model,
                session_db_path=runtime.session_db_path,
                tracing_enabled=runtime.tracing_enabled,
                trace_group_id=task.session_id,
                manager_trace_id=gen_trace_id() if runtime.tracing_enabled and gen_trace_id is not None else None,
            )
            factory = ResearchAgentFactory(
                model=runtime.model,
                session_db_path=runtime.session_db_path,
                tracing_enabled=runtime.tracing_enabled,
                base_url=runtime.openai_base_url,
                schema_debug_enabled=True,
                provider_timeout_seconds=runtime.provider_timeout_seconds,
            )

            results: list[dict[str, Any]] = []
            requested_paths = ["structured", "plain_json_fallback"] if args.path == "both" else [args.path]
            for path_label in requested_paths:
                results.append(
                    _run_provider_path(
                        factory=factory,
                        context=context,
                        task=task,
                        structured=path_label == "structured",
                    )
                )

            payload = {
                "case_id": args.case_id,
                "task_type": task.task_type,
                "requested_runtime_mode": "agents_sdk",
                "strict_mode": True,
                "mock_fallback_allowed": False,
                "results": results,
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0 if all(item.get("ok") for item in results) else 1
        finally:
            service.shutdown(wait=True)


if __name__ == "__main__":
    raise SystemExit(main())
