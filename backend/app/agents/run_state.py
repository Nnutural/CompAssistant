from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.schemas.research_runtime import (
    AgentTaskEnvelope,
    ControlRecord,
    ResearchLedger,
    RunEvent,
    RunState,
    RuntimeArtifact,
    ValidationIssue,
    ValidationIssueKind,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def reset_run_tracking(
    ledger: ResearchLedger,
    task: AgentTaskEnvelope,
    *,
    model: str | None = None,
    base_url: str | None = None,
    requested_runtime_mode: str | None = None,
    effective_runtime_mode: str | None = None,
    effective_model: str | None = None,
) -> None:
    ledger.run_id = task.task_id
    ledger.task_type = task.task_type
    ledger.current_state = None
    ledger.completed_states = []
    ledger.error_stage = None
    ledger.events = []
    ledger.raw_outputs = {}
    ledger.repaired_outputs = {}
    ledger.validation_errors = []
    ledger.parse_errors = []
    ledger.artifacts = []
    ledger.model = model or ledger.model
    ledger.base_url = base_url or ledger.base_url
    ledger.requested_runtime_mode = requested_runtime_mode or ledger.requested_runtime_mode
    ledger.effective_runtime_mode = effective_runtime_mode or ledger.effective_runtime_mode
    ledger.effective_model = effective_model or ledger.effective_model
    ledger.used_mock_fallback = False
    ledger.fallback_reason = None
    ledger.elapsed_ms = None
    ledger.result_status = None
    ledger.result_summary = None
    ledger.follow_up_items = []
    ledger.blockers = []
    ledger.finding_count = 0
    ledger.updated_at = utc_now()


def transition_state(
    ledger: ResearchLedger,
    state: RunState,
    *,
    actor: str,
    message: str,
    detail: dict[str, Any] | None = None,
) -> None:
    if ledger.current_state in {"completed", "cancelled", "failed", "awaiting_review"} and state not in {
        "completed",
        "cancelled",
        "failed",
        "awaiting_review",
    }:
        return
    previous = ledger.current_state
    if previous and previous != state and previous not in ("failed", "awaiting_review", "completed", "cancelled"):
        mark_state_completed(ledger, previous, actor=actor, message=f"{previous} completed.")
    ledger.current_state = state
    ledger.updated_at = utc_now()
    append_event(ledger, state=state, status="entered", actor=actor, message=message, detail=detail)


def mark_state_completed(
    ledger: ResearchLedger,
    state: RunState,
    *,
    actor: str,
    message: str,
    detail: dict[str, Any] | None = None,
) -> None:
    if state not in ledger.completed_states:
        ledger.completed_states.append(state)
    ledger.updated_at = utc_now()
    append_event(ledger, state=state, status="completed", actor=actor, message=message, detail=detail)


def append_event(
    ledger: ResearchLedger,
    *,
    state: RunState,
    status: str,
    actor: str,
    message: str,
    detail: dict[str, Any] | None = None,
) -> None:
    run_id = ledger.run_id or ledger.ledger_id
    ledger.events.append(
        RunEvent(
            event_id=f"{run_id}-event-{len(ledger.events) + 1}",
            state=state,
            status=status,
            actor=actor,
            message=message,
            detail=detail,
            created_at=utc_now(),
        )
    )


def record_output(ledger: ResearchLedger, *, stage: str, payload: Any, repaired: bool = False) -> None:
    target = ledger.repaired_outputs if repaired else ledger.raw_outputs
    target[stage] = _to_jsonable(payload)
    ledger.updated_at = utc_now()


def record_issue(
    ledger: ResearchLedger,
    *,
    stage: str,
    kind: ValidationIssueKind,
    message: str,
    agent: str | None = None,
    detail: str | None = None,
) -> None:
    issue = ValidationIssue(
        stage=stage,
        kind=kind,
        message=message,
        agent=agent,
        detail=detail,
        created_at=utc_now(),
    )
    if kind == "parse_error":
        ledger.parse_errors.append(issue)
    else:
        ledger.validation_errors.append(issue)
    append_event(
        ledger,
        state=ledger.current_state or "reasoning",
        status="warning" if kind == "repair_warning" else "error",
        actor=agent or "runtime",
        message=message,
        detail={"stage": stage, "kind": kind},
    )
    ledger.updated_at = utc_now()


def record_artifact(
    ledger: ResearchLedger,
    *,
    artifact_id: str,
    artifact_type: str,
    title: str,
    payload: Any,
) -> None:
    ledger.artifacts.append(
        RuntimeArtifact(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            title=title,
            payload=_to_jsonable(payload),
            created_at=utc_now(),
        )
    )
    ledger.updated_at = utc_now()


def mark_fallback(ledger: ResearchLedger, *, reason: str, actor: str) -> None:
    ledger.used_mock_fallback = True
    ledger.fallback_reason = reason
    append_event(
        ledger,
        state=ledger.current_state or "reasoning",
        status="fallback",
        actor=actor,
        message=reason,
        detail={"used_mock_fallback": True},
    )
    ledger.updated_at = utc_now()


def mark_review_required(
    ledger: ResearchLedger,
    *,
    actor: str,
    message: str,
    elapsed_ms: float | None = None,
) -> None:
    if ledger.current_state and ledger.current_state not in ledger.completed_states:
        mark_state_completed(ledger, ledger.current_state, actor=actor, message=f"{ledger.current_state} completed.")
    ledger.current_state = "awaiting_review"
    ledger.elapsed_ms = elapsed_ms
    ledger.updated_at = utc_now()
    append_event(ledger, state="awaiting_review", status="warning", actor=actor, message=message)


def mark_cancelled(
    ledger: ResearchLedger,
    *,
    actor: str,
    message: str,
    elapsed_ms: float | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    if ledger.current_state and ledger.current_state not in ledger.completed_states:
        mark_state_completed(ledger, ledger.current_state, actor=actor, message=f"{ledger.current_state} completed.")
    ledger.current_state = "cancelled"
    ledger.elapsed_ms = elapsed_ms
    ledger.updated_at = utc_now()
    append_event(ledger, state="cancelled", status="warning", actor=actor, message=message, detail=detail)


def mark_completed(
    ledger: ResearchLedger,
    *,
    actor: str,
    message: str,
    elapsed_ms: float,
) -> None:
    if ledger.current_state and ledger.current_state not in ledger.completed_states:
        mark_state_completed(ledger, ledger.current_state, actor=actor, message=f"{ledger.current_state} completed.")
    ledger.current_state = "completed"
    if "completed" not in ledger.completed_states:
        ledger.completed_states.append("completed")
    ledger.elapsed_ms = elapsed_ms
    ledger.updated_at = utc_now()
    append_event(ledger, state="completed", status="completed", actor=actor, message=message)


def mark_failed(
    ledger: ResearchLedger,
    *,
    stage: RunState,
    actor: str,
    message: str,
    detail: str | None = None,
    elapsed_ms: float | None = None,
) -> None:
    ledger.error_stage = stage
    ledger.current_state = "failed"
    ledger.elapsed_ms = elapsed_ms
    ledger.updated_at = utc_now()
    append_event(
        ledger,
        state="failed",
        status="error",
        actor=actor,
        message=message,
        detail={"stage": stage, "detail": detail} if detail else {"stage": stage},
    )


def record_control_action(
    ledger: ResearchLedger,
    *,
    action: str,
    actor: str,
    note: str | None = None,
    related_run_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    ledger.control_records.append(
        ControlRecord(
            action_id=f"{ledger.run_id or ledger.ledger_id}-control-{len(ledger.control_records) + 1}",
            action=action,
            actor=actor,
            note=note,
            related_run_id=related_run_id,
            metadata=metadata or {},
            created_at=utc_now(),
        )
    )
    ledger.updated_at = utc_now()


def _to_jsonable(payload: Any) -> Any:
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json", exclude_none=True)
    if isinstance(payload, list):
        return [_to_jsonable(item) for item in payload]
    if isinstance(payload, tuple):
        return [_to_jsonable(item) for item in payload]
    if isinstance(payload, dict):
        return {str(key): _to_jsonable(value) for key, value in payload.items()}
    return payload
