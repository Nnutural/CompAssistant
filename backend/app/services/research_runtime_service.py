from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from time import perf_counter
from typing import Iterable, Optional
from uuid import uuid4

from app.agents.manager import ResearchRuntimeManager
from app.agents.run_state import (
    append_event,
    mark_completed,
    mark_cancelled,
    mark_failed,
    mark_fallback,
    mark_review_required,
    record_control_action,
    reset_run_tracking,
    transition_state,
)
from app.agents.sdk_runtime import AgentsSDKResearchRuntime
from app.core.config import Settings, settings
from app.repositories.ledger_repository import LedgerRepository
from app.runtime_modes import resolve_runtime_mode
from app.schemas.agent_tasks import (
    AgentTaskArtifactItem,
    AgentTaskArtifactsResponse,
    AgentTaskCancelRequest,
    AgentTaskCreateRequest,
    AgentTaskControlResponse,
    AgentTaskEventItem,
    AgentTaskEventsResponse,
    AgentTaskHistoryItem,
    AgentTaskHistoryResponse,
    AgentTaskResultSummary,
    AgentTaskRetryResponse,
    AgentTaskReviewRequest,
    AgentTaskStatusResponse,
)
from app.schemas.research_runtime import AgentResult, AgentTaskEnvelope, ArtifactItem, ResearchLedger, ResearchScope

logger = logging.getLogger("uvicorn.error")
TERMINAL_RUN_STATES = {"completed", "cancelled", "failed", "awaiting_review"}
ACTIVE_RUN_STATES = {
    "queued",
    "running",
    "planning",
    "retrieving_local_context",
    "reasoning",
    "validating_output",
    "persisting_artifacts",
}


class TaskConflictError(RuntimeError):
    pass


class TaskControlError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


class TaskCancelledError(RuntimeError):
    def __init__(self, message: str):
        super().__init__(message)


@dataclass
class BackgroundRunHandle:
    run_id: str
    session_id: str
    task_type: str
    submitted_at: datetime
    future: Future
    ledger: ResearchLedger
    cancel_requested: bool = False
    cancel_note: str | None = None


class ResearchRuntimeService:
    def __init__(
        self,
        repository: Optional[LedgerRepository] = None,
        manager: Optional[ResearchRuntimeManager] = None,
        sdk_runtime: Optional[AgentsSDKResearchRuntime] = None,
        settings_obj: Optional[Settings] = None,
        runtime_mode: Optional[str] = None,
        strict_mode: Optional[bool] = None,
        background_executor: Optional[ThreadPoolExecutor] = None,
    ):
        self.settings = settings_obj or settings
        self.repository = repository or LedgerRepository()
        self.manager = manager or ResearchRuntimeManager()
        self.sdk_runtime = sdk_runtime
        resolved_runtime_mode = resolve_runtime_mode(runtime_mode or self.settings.research_runtime_mode)
        self.requested_runtime_mode = resolved_runtime_mode.requested_runtime_mode
        self.runtime_mode = resolved_runtime_mode.normalized_runtime_mode
        self.strict_mode = self.settings.research_runtime_strict_mode if strict_mode is None else strict_mode
        self._executor = background_executor or ThreadPoolExecutor(max_workers=4, thread_name_prefix="agent-task")
        self._owns_executor = background_executor is None
        self._background_runs: dict[str, BackgroundRunHandle] = {}
        self._background_lock = RLock()

    def shutdown(self, *, wait: bool = True) -> None:
        if self._owns_executor:
            self._executor.shutdown(wait=wait, cancel_futures=False)

    def run_task(self, task: AgentTaskEnvelope) -> AgentResult:
        ledger = self._load_or_create_ledger(task)
        return self._run_task_with_ledger(task, ledger, queued_execution=False)

    def get_ledger(self, ledger_id: str) -> Optional[ResearchLedger]:
        return self.repository.get(ledger_id)

    def list_ledgers(self) -> list[ResearchLedger]:
        return self.repository.list()

    def create_agent_task(self, request: AgentTaskCreateRequest) -> AgentTaskStatusResponse:
        run_id = request.task_id or f"run-{uuid4().hex[:12]}"
        session_id = request.session_id or run_id
        envelope = AgentTaskEnvelope(
            contract_version="1.0",
            task_id=run_id,
            session_id=session_id,
            task_type=request.task_type,
            requested_by=request.requested_by,
            priority=request.priority,
            objective=request.objective or self._default_objective_for(request.task_type),
            payload=request.payload,
            constraints=request.constraints,
            dry_run=request.dry_run,
            created_at=datetime.now(timezone.utc),
        )

        with self._background_lock:
            self._ensure_task_creation_available(envelope, explicit_task_id=request.task_id is not None)
            ledger = self._load_or_create_ledger(envelope)
            self._prepare_task_for_background(ledger, envelope)
            initial_status = self._build_task_status_response(ledger, run_id)
            try:
                future = self._executor.submit(self._run_task_in_background, envelope, ledger)
            except Exception as exc:
                ledger.result_status = "blocked"
                ledger.result_summary = f"Unable to submit background task: {exc}"
                ledger.blockers = [str(exc)]
                ledger.status = "paused"
                mark_failed(
                    ledger,
                    stage="queued",
                    actor="service",
                    message=f"Unable to submit background task: {exc}",
                    detail=str(exc),
                )
                self.repository.update(ledger)
                raise

            self._background_runs[run_id] = BackgroundRunHandle(
                run_id=run_id,
                session_id=session_id,
                task_type=envelope.task_type,
                submitted_at=datetime.now(timezone.utc),
                future=future,
                ledger=ledger,
            )
            future.add_done_callback(lambda completed_future, current_run_id=run_id: self._on_background_done(current_run_id, completed_future))
            return initial_status

    def get_task_status(self, run_id: str) -> Optional[AgentTaskStatusResponse]:
        ledger = self.repository.find_by_run_id(run_id)
        if ledger is None:
            return None
        return self._build_task_status_response(ledger, run_id)

    def get_task_events(self, run_id: str) -> Optional[AgentTaskEventsResponse]:
        ledger = self.repository.find_by_run_id(run_id)
        if ledger is None:
            return None
        items = [
            AgentTaskEventItem(
                event_id=item.event_id,
                run_id=ledger.run_id or run_id,
                state=item.state,
                status=item.status,
                message=item.message,
                actor=item.actor,
                detail=item.detail,
                created_at=item.created_at,
            )
            for item in ledger.events
        ]
        return AgentTaskEventsResponse(
            run_id=ledger.run_id or run_id,
            task_id=ledger.run_id or run_id,
            task_type=ledger.task_type,
            current_state=ledger.current_state,
            items=items,
        )

    def get_task_artifacts(self, run_id: str) -> Optional[AgentTaskArtifactsResponse]:
        ledger = self.repository.find_by_run_id(run_id)
        if ledger is None:
            return None
        items: list[AgentTaskArtifactItem] = []
        if ledger.current_state in TERMINAL_RUN_STATES:
            items.extend(
                [
                    AgentTaskArtifactItem(
                        artifact_id=item.artifact_id,
                        run_id=ledger.run_id or run_id,
                        artifact_type=item.artifact_type,
                        title=item.title,
                        payload=item.payload,
                        created_at=item.created_at,
                    )
                    for item in ledger.artifacts
                ]
            )
        if not items and ledger.current_state in TERMINAL_RUN_STATES:
            items.extend(
                [
                    AgentTaskArtifactItem(
                        artifact_id=f"{ledger.run_id or run_id}-ref-{index}",
                        run_id=ledger.run_id or run_id,
                        artifact_type=item.kind,
                        title=item.title or item.ref,
                        ref=item.ref,
                    )
                    for index, item in enumerate(ledger.final_artifacts, start=1)
                ]
            )
        return AgentTaskArtifactsResponse(
            run_id=ledger.run_id or run_id,
            task_id=ledger.run_id or run_id,
            task_type=ledger.task_type,
            current_state=ledger.current_state,
            items=items,
        )

    def list_agent_tasks(
        self,
        *,
        status_filter: str | None = None,
        task_type_filter: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> AgentTaskHistoryResponse:
        ledgers = [ledger for ledger in self.repository.list() if ledger.run_id]
        items: list[AgentTaskHistoryItem] = []
        for ledger in ledgers:
            status_value = self._derive_task_run_status(ledger)
            if status_filter and status_value != status_filter:
                continue
            if task_type_filter and ledger.task_type != task_type_filter:
                continue
            artifact_count = self._derive_artifact_count(ledger)
            items.append(
                AgentTaskHistoryItem(
                    run_id=ledger.run_id or ledger.ledger_id,
                    task_id=ledger.run_id or ledger.ledger_id,
                    session_id=ledger.session_id,
                    ledger_id=ledger.ledger_id,
                    task_type=ledger.task_type,
                    status=status_value,
                    current_state=ledger.current_state,
                    result_status=ledger.result_status,
                    result_summary=ledger.result_summary,
                    artifact_count=artifact_count,
                    has_artifacts=artifact_count > 0,
                    awaiting_review=ledger.current_state == "awaiting_review",
                    requested_runtime_mode=ledger.requested_runtime_mode,
                    effective_runtime_mode=ledger.effective_runtime_mode,
                    effective_model=ledger.effective_model,
                    provider_success_path=self._derive_provider_success_path(ledger),
                    used_mock_fallback=ledger.used_mock_fallback,
                    parent_run_id=ledger.parent_run_id,
                    available_actions=self._derive_available_actions(ledger),
                    created_at=ledger.created_at,
                    updated_at=ledger.updated_at,
                )
            )
        items.sort(key=lambda item: item.updated_at or item.created_at, reverse=True)
        total = len(items)
        sliced = items[offset : offset + limit]
        return AgentTaskHistoryResponse(items=sliced, total=total, limit=limit, offset=offset)

    def retry_agent_task(self, run_id: str) -> AgentTaskRetryResponse:
        source = self.repository.find_by_run_id(run_id)
        if source is None or not source.run_id:
            raise TaskControlError("Agent task not found", status_code=404)
        if self._derive_task_run_status(source) not in {"completed", "cancelled", "failed", "awaiting_review"}:
            raise TaskControlError("Retry is only available for terminal tasks.")

        request = self._build_retry_request(source)
        record_control_action(
            source,
            action="retry",
            actor="operator",
            note="Retry requested from agent task API.",
            related_run_id=request.task_id,
            metadata={"new_run_id": request.task_id},
        )
        append_event(
            source,
            state=source.current_state or "completed",
            status="info",
            actor="operator",
            message=f"Retry requested. New run created: {request.task_id}",
            detail={"new_run_id": request.task_id},
        )
        self.repository.update(source)

        new_run = self.create_agent_task(request)
        return AgentTaskRetryResponse(
            action="retry",
            source_run_id=run_id,
            new_run=new_run,
            message="Retry task created successfully.",
        )

    def cancel_agent_task(self, run_id: str, request: AgentTaskCancelRequest) -> AgentTaskControlResponse:
        ledger = self.repository.find_by_run_id(run_id)
        if ledger is None or not ledger.run_id:
            raise TaskControlError("Agent task not found", status_code=404)
        if self._derive_task_run_status(ledger) not in {"queued", "running"}:
            raise TaskControlError("Cancel is only available for queued or running tasks.")

        note = request.note or "Task cancelled by operator."
        with self._background_lock:
            handle = self._background_runs.get(run_id)
            target_ledger = handle.ledger if handle is not None else ledger
            if handle is not None:
                handle.cancel_requested = True
                handle.cancel_note = note
                handle.future.cancel()
            target_ledger.result_status = "blocked"
            target_ledger.result_summary = note
            if note not in target_ledger.blockers:
                target_ledger.blockers.append(note)
            target_ledger.status = "paused"
            record_control_action(
                target_ledger,
                action="cancel",
                actor="operator",
                note=note,
            )
            mark_cancelled(
                target_ledger,
                actor="operator",
                message=note,
                detail={"requested_via": "api"},
            )
            self.repository.update(target_ledger)

        return AgentTaskControlResponse(
            action="cancel",
            message="Task cancellation recorded.",
            task=self._build_task_status_response(target_ledger, run_id),
        )

    def review_agent_task(self, run_id: str, request: AgentTaskReviewRequest) -> AgentTaskControlResponse:
        ledger = self.repository.find_by_run_id(run_id)
        if ledger is None or not ledger.run_id:
            raise TaskControlError("Agent task not found", status_code=404)
        if ledger.current_state != "awaiting_review":
            raise TaskControlError("Review is only available for awaiting_review tasks.")

        note = request.note or self._default_review_note(request.decision)
        if request.decision == "accept":
            ledger.status = "completed"
            ledger.result_status = "completed"
            ledger.result_summary = note
            record_control_action(ledger, action="review_accept", actor="operator", note=note)
            mark_completed(ledger, actor="operator", message=note, elapsed_ms=ledger.elapsed_ms or 0.0)
            action = "review_accept"
            message = "Review accepted and task marked as completed."
        elif request.decision == "reject":
            ledger.status = "paused"
            ledger.result_status = "blocked"
            ledger.result_summary = note
            if note not in ledger.blockers:
                ledger.blockers.append(note)
            record_control_action(ledger, action="review_reject", actor="operator", note=note)
            mark_failed(
                ledger,
                stage="awaiting_review",
                actor="operator",
                message=note,
                detail="review_reject",
                elapsed_ms=ledger.elapsed_ms,
            )
            action = "review_reject"
            message = "Review rejected and task marked as failed."
        else:
            ledger.status = "paused"
            record_control_action(ledger, action="review_annotate", actor="operator", note=note)
            append_event(
                ledger,
                state="awaiting_review",
                status="info",
                actor="operator",
                message=note,
                detail={"decision": "annotate"},
            )
            if note not in ledger.follow_up_items:
                ledger.follow_up_items.append(note)
            ledger.updated_at = datetime.now(timezone.utc)
            action = "review_annotate"
            message = "Review note recorded."
        self.repository.update(ledger)
        return AgentTaskControlResponse(
            action=action,
            message=message,
            task=self._build_task_status_response(ledger, run_id),
        )

    def _run_task_in_background(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> None:
        self._run_task_with_ledger(task, ledger, queued_execution=True)

    def _on_background_done(self, run_id: str, future: Future) -> None:
        with self._background_lock:
            self._background_runs.pop(run_id, None)
        if future.cancelled():
            logger.info("[research-runtime] background run cancelled before start run_id=%s", run_id)
            return
        error = future.exception()
        if error is not None:
            if isinstance(error, TaskCancelledError):
                logger.info("[research-runtime] background run cancelled run_id=%s", run_id)
                return
            logger.warning("[research-runtime] background run finished with error run_id=%s error=%s", run_id, error)
            return
        logger.info("[research-runtime] background run completed run_id=%s", run_id)

    def _run_task_with_ledger(
        self,
        task: AgentTaskEnvelope,
        ledger: ResearchLedger,
        *,
        queued_execution: bool,
    ) -> AgentResult:
        started_at = perf_counter()
        logger.info(
            "[research-runtime] run_task start task_id=%s session_id=%s runtime_mode=%s strict_mode=%s queued_execution=%s",
            task.task_id,
            task.session_id,
            self.runtime_mode,
            self.strict_mode,
            queued_execution,
        )
        if queued_execution:
            self._abort_if_cancelled(task.task_id, ledger)
            transition_state(
                ledger,
                "running",
                actor="service",
                message="任务已开始在后台执行。",
            )
            self.repository.update(ledger)
        self._prepare_run(ledger, task, reset_tracking=not queued_execution)

        try:
            self._abort_if_cancelled(task.task_id, ledger)
            result, updated_ledger = self._run_runtime(task, ledger)
            self._abort_if_cancelled(task.task_id, updated_ledger)
            review_required = updated_ledger.current_state == "awaiting_review" or result.status == "needs_human"
            review_message = result.follow_up_items[-1] if result.follow_up_items else "Run requires manual review."
            transition_state(
                updated_ledger,
                "persisting_artifacts",
                actor="service",
                message="正在持久化本次运行的产物与 ledger 状态。",
            )
            self.repository.update(updated_ledger)

            elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
            if review_required:
                updated_ledger.status = "paused"
                mark_review_required(
                    updated_ledger,
                    actor="service",
                    message=review_message,
                    elapsed_ms=elapsed_ms,
                )
            else:
                updated_ledger.status = "completed"
                mark_completed(
                    updated_ledger,
                    actor="service",
                    message="任务已完成，结果已持久化。",
                    elapsed_ms=elapsed_ms,
                )
            self.repository.update(updated_ledger)
        except TaskCancelledError as exc:
            elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
            if ledger.current_state != "cancelled":
                ledger.status = "paused"
                ledger.result_status = "blocked"
                ledger.result_summary = str(exc)
                if str(exc) not in ledger.blockers:
                    ledger.blockers.append(str(exc))
                record_control_action(ledger, action="cancel", actor="service", note=str(exc))
                mark_cancelled(
                    ledger,
                    actor="service",
                    message=str(exc),
                    elapsed_ms=elapsed_ms,
                    detail={"run_id": task.task_id},
                )
            else:
                ledger.elapsed_ms = elapsed_ms
            self.repository.update(ledger)
            raise
        except Exception as exc:
            elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
            ledger.result_status = "blocked"
            ledger.result_summary = f"Run failed: {exc}"
            ledger.blockers = [str(exc)]
            mark_failed(
                ledger,
                stage=ledger.current_state or "planning",
                actor="service",
                message=f"任务执行失败：{exc}",
                detail=str(exc),
                elapsed_ms=elapsed_ms,
            )
            ledger.status = "paused"
            self.repository.update(ledger)
            raise

        changed_path = self._to_repo_relative(self.repository.get_storage_path(updated_ledger.ledger_id))
        if changed_path not in result.changed_paths:
            result.changed_paths.append(changed_path)
        if not any(item.kind == "ledger_entry" and item.ref == updated_ledger.ledger_id for item in result.artifacts):
            result.artifacts.append(
                ArtifactItem(kind="ledger_entry", ref=updated_ledger.ledger_id, title="Research Ledger entry")
            )
        logger.info(
            "[research-runtime] run_task completed task_id=%s ledger_id=%s status=%s findings=%s artifacts=%s task_history=%s evidence_log=%s changed_path=%s elapsed_ms=%.2f",
            task.task_id,
            updated_ledger.ledger_id,
            result.status,
            len(result.findings),
            len(result.artifacts),
            len(updated_ledger.task_history),
            len(updated_ledger.evidence_log),
            changed_path,
            (perf_counter() - started_at) * 1000,
        )
        return result

    def _run_runtime(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> tuple[AgentResult, ResearchLedger]:
        runtime_started_at = perf_counter()
        checkpoint_callback = self._build_checkpoint_callback(task.task_id)
        abort_if_requested = lambda active_ledger: self._abort_if_cancelled(task.task_id, active_ledger)
        if self.runtime_mode == "agents_sdk":
            try:
                logger.info(
                    "[research-runtime] selecting agents_sdk runtime task_id=%s ledger_id=%s",
                    task.task_id,
                    ledger.ledger_id,
                )
                runtime = self._get_sdk_runtime()
                if not runtime.is_available():
                    raise RuntimeError(
                        "Ark chat-completions runtime is unavailable because OPENAI_API_KEY or SDK dependencies are missing."
                    )
                result, updated_ledger = runtime.run(
                    task,
                    ledger,
                    checkpoint_callback=checkpoint_callback,
                    abort_if_requested=abort_if_requested,
                )
                updated_ledger.requested_runtime_mode = self.requested_runtime_mode
                updated_ledger.effective_runtime_mode = "agents_sdk"
                updated_ledger.effective_model = self.settings.openai_default_model
                logger.info(
                    "[research-runtime] agents_sdk runtime finished task_id=%s ledger_id=%s status=%s elapsed_ms=%.2f",
                    task.task_id,
                    ledger.ledger_id,
                    result.status,
                    (perf_counter() - runtime_started_at) * 1000,
                )
                return result, updated_ledger
            except Exception as exc:
                note = f"Ark chat-completions runtime failed: {exc}"
                logger.warning(
                    "[research-runtime] agents_sdk runtime failed task_id=%s ledger_id=%s strict_mode=%s error=%s",
                    task.task_id,
                    ledger.ledger_id,
                    self.strict_mode,
                    exc,
                )
                if self.strict_mode:
                    raise RuntimeError(note) from exc
                ledger.requested_runtime_mode = self.requested_runtime_mode
                ledger.effective_runtime_mode = "mock"
                ledger.effective_model = "mock"
                mark_fallback(ledger, reason=note, actor="service")
                self.repository.update(ledger)
                return self._run_mock_with_note(task, ledger, note)

        logger.info(
            "[research-runtime] selecting mock runtime task_id=%s ledger_id=%s",
            task.task_id,
            ledger.ledger_id,
        )
        result, updated_ledger = self.manager.run(
            task,
            ledger,
            checkpoint_callback=checkpoint_callback,
            abort_if_requested=abort_if_requested,
        )
        logger.info(
            "[research-runtime] mock runtime finished task_id=%s ledger_id=%s status=%s elapsed_ms=%.2f",
            task.task_id,
            ledger.ledger_id,
            result.status,
            (perf_counter() - runtime_started_at) * 1000,
        )
        return result, updated_ledger

    def _get_sdk_runtime(self) -> AgentsSDKResearchRuntime:
        if self.sdk_runtime is None:
            self.sdk_runtime = AgentsSDKResearchRuntime(
                model=self.settings.openai_default_model,
                openai_api_key=self.settings.openai_api_key,
                openai_base_url=self.settings.openai_base_url,
                tracing_enabled=self.settings.research_runtime_tracing_enabled,
                schema_debug_enabled=self.settings.research_runtime_schema_debug,
                provider_timeout_seconds=self.settings.research_runtime_provider_timeout_seconds,
                session_db_path=self.settings.research_runtime_session_db,
            )
        return self.sdk_runtime

    def _run_mock_with_note(
        self,
        task: AgentTaskEnvelope,
        ledger: ResearchLedger,
        note: str,
    ) -> tuple[AgentResult, ResearchLedger]:
        fallback_started_at = perf_counter()
        checkpoint_callback = self._build_checkpoint_callback(task.task_id)
        abort_if_requested = lambda active_ledger: self._abort_if_cancelled(task.task_id, active_ledger)
        logger.info(
            "[research-runtime] falling back to mock runtime task_id=%s ledger_id=%s reason=%s",
            task.task_id,
            ledger.ledger_id,
            note,
        )
        result, updated_ledger = self.manager.run(
            task,
            ledger,
            checkpoint_callback=checkpoint_callback,
            abort_if_requested=abort_if_requested,
        )
        fallback_note = f"Returned mock-derived result because {note}"
        if fallback_note not in result.follow_up_items:
            result.follow_up_items.insert(0, fallback_note)
        if note not in updated_ledger.synthesis_notes:
            updated_ledger.synthesis_notes.append(note)
        updated_ledger.effective_runtime_mode = "mock"
        updated_ledger.effective_model = "mock"
        updated_ledger.used_mock_fallback = True
        updated_ledger.fallback_reason = note
        fallback_metadata = [
            f"requested runtime mode: {self.requested_runtime_mode}",
            f"runtime model: {self.settings.openai_default_model}",
            "effective runtime mode: mock",
            "effective model: mock",
            f"runtime base url: {self.settings.openai_base_url}",
            f"tracing enabled: {str(bool(self.settings.research_runtime_tracing_enabled)).lower()}",
            "used mock fallback: true",
            f"fallback reason: {note}",
        ]
        for metadata_note in fallback_metadata:
            if metadata_note not in updated_ledger.synthesis_notes:
                updated_ledger.synthesis_notes.append(metadata_note)
        logger.info(
            "[research-runtime] mock fallback completed task_id=%s ledger_id=%s status=%s elapsed_ms=%.2f",
            task.task_id,
            ledger.ledger_id,
            result.status,
            (perf_counter() - fallback_started_at) * 1000,
        )
        return result, updated_ledger

    def _prepare_run(self, ledger: ResearchLedger, task: AgentTaskEnvelope, *, reset_tracking: bool) -> None:
        model = self._requested_model()
        base_url = self._requested_base_url()
        if reset_tracking:
            reset_run_tracking(
                ledger,
                task,
                model=model,
                base_url=base_url,
                requested_runtime_mode=self.requested_runtime_mode,
                effective_runtime_mode=self._effective_runtime_mode_for_request(),
                effective_model=self._effective_model_for_request(),
            )
            transition_state(ledger, "received", actor="service", message="Task received by runtime service.")
        else:
            ledger.model = model
            ledger.base_url = base_url
            ledger.requested_runtime_mode = self.requested_runtime_mode
            ledger.effective_runtime_mode = self._effective_runtime_mode_for_request()
            ledger.effective_model = self._effective_model_for_request()
            ledger.updated_at = datetime.now(timezone.utc)
        transition_state(ledger, "planning", actor="service", message="正在规划运行路径与状态机阶段。")
        ledger.status = "active"
        self.repository.update(ledger)

    def _prepare_task_for_background(self, ledger: ResearchLedger, task: AgentTaskEnvelope) -> None:
        model = self._requested_model()
        base_url = self._requested_base_url()
        reset_run_tracking(
            ledger,
            task,
            model=model,
            base_url=base_url,
            requested_runtime_mode=self.requested_runtime_mode,
            effective_runtime_mode=self._effective_runtime_mode_for_request(),
            effective_model=self._effective_model_for_request(),
        )
        ledger.request_objective = task.objective
        ledger.request_payload = dict(task.payload)
        ledger.request_constraints = list(task.constraints)
        transition_state(ledger, "received", actor="service", message="任务已通过 Agent Task API 创建。")
        transition_state(ledger, "queued", actor="service", message="任务已进入后台执行队列。")
        ledger.status = "active"
        self.repository.update(ledger)

    def _load_or_create_ledger(self, task: AgentTaskEnvelope) -> ResearchLedger:
        ledger_id = self._resolve_ledger_id(task)
        existing = self.repository.get(ledger_id)
        if existing:
            logger.info(
                "[research-runtime] reusing existing ledger ledger_id=%s session_id=%s",
                ledger_id,
                task.session_id,
            )
            return existing

        timestamp = task.created_at or datetime.now(timezone.utc)
        topic = str(task.payload.get("topic") or task.objective)
        question = str(task.payload.get("research_question") or task.objective)
        scope = ResearchScope(
            included_topics=self._coerce_str_list(task.payload.get("included_topics"), default=[topic]),
            excluded_topics=self._coerce_str_list(task.payload.get("excluded_topics"), default=[]),
            success_criteria=self._coerce_str_list(
                task.payload.get("success_criteria"),
                default=["Return AgentResult", "Persist the Research Ledger"],
            ),
        )
        ledger = ResearchLedger(
            contract_version="1.0",
            ledger_id=ledger_id,
            session_id=task.session_id,
            topic=topic,
            research_question=question,
            status="active",
            owner=task.requested_by,
            parent_run_id=self._coerce_parent_run_id(task.payload),
            scope=scope,
            hypotheses=self._coerce_str_list(task.payload.get("hypotheses"), default=[]),
            task_history=[],
            source_registry=[],
            evidence_log=[],
            synthesis_notes=[],
            final_artifacts=[],
            open_questions=self._coerce_str_list(task.payload.get("open_questions"), default=[]),
            request_objective=task.objective,
            request_payload=dict(task.payload),
            request_constraints=list(task.constraints),
            requested_runtime_mode=self.requested_runtime_mode,
            effective_runtime_mode=self._effective_runtime_mode_for_request(),
            effective_model=self._effective_model_for_request(),
            created_at=timestamp,
            updated_at=timestamp,
        )
        logger.info(
            "[research-runtime] creating new ledger ledger_id=%s session_id=%s topic=%s",
            ledger_id,
            task.session_id,
            topic,
        )
        return self.repository.create(ledger)

    def _ensure_task_creation_available(self, task: AgentTaskEnvelope, *, explicit_task_id: bool) -> None:
        if explicit_task_id and self.repository.find_by_run_id(task.task_id) is not None:
            raise TaskConflictError(f"Agent task already exists for task_id={task.task_id}")

        ledger_id = self._resolve_ledger_id(task)
        existing = self.repository.get(ledger_id)
        if existing is None:
            return
        if existing.run_id == task.task_id:
            raise TaskConflictError(f"Agent task already exists for task_id={task.task_id}")
        if existing.current_state not in TERMINAL_RUN_STATES:
            raise TaskConflictError(
                f"An active agent task already exists for session_id={task.session_id} and ledger_id={ledger_id}"
            )

    def _resolve_ledger_id(self, task: AgentTaskEnvelope) -> str:
        payload_ledger_id = task.payload.get("ledger_id")
        if isinstance(payload_ledger_id, str) and payload_ledger_id.strip():
            return payload_ledger_id.strip()
        return f"ledger-{task.session_id}"

    def _coerce_parent_run_id(self, payload: dict[str, object]) -> str | None:
        parent_run_id = payload.get("_parent_run_id")
        if isinstance(parent_run_id, str) and parent_run_id.strip():
            return parent_run_id.strip()
        return None

    def _requested_model(self) -> str:
        return self.settings.openai_default_model if self.runtime_mode == "agents_sdk" else "mock"

    def _requested_base_url(self) -> str | None:
        return self.settings.openai_base_url if self.runtime_mode == "agents_sdk" else None

    def _effective_runtime_mode_for_request(self) -> str:
        return "agents_sdk" if self.runtime_mode == "agents_sdk" else "mock"

    def _effective_model_for_request(self) -> str:
        return self.settings.openai_default_model if self.runtime_mode == "agents_sdk" else "mock"

    def _coerce_str_list(self, value, default: Iterable[str]) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return list(default)

    def _to_repo_relative(self, path) -> str:
        repo_root = path.resolve().parents[3]
        return path.resolve().relative_to(repo_root).as_posix()

    def _build_task_status_response(self, ledger: ResearchLedger, run_id: str) -> AgentTaskStatusResponse:
        artifact_count = self._derive_artifact_count(ledger)
        return AgentTaskStatusResponse(
            run_id=ledger.run_id or run_id,
            task_id=ledger.run_id or run_id,
            session_id=ledger.session_id,
            ledger_id=ledger.ledger_id,
            task_type=ledger.task_type,
            status=self._derive_task_run_status(ledger),
            current_state=ledger.current_state,
            completed_states=ledger.completed_states,
            error_stage=ledger.error_stage,
            result=AgentTaskResultSummary(
                status=ledger.result_status,
                summary=ledger.result_summary,
                finding_count=ledger.finding_count,
                follow_up_items=ledger.follow_up_items,
                blockers=ledger.blockers,
            ),
            requested_runtime_mode=ledger.requested_runtime_mode,
            effective_runtime_mode=ledger.effective_runtime_mode,
            effective_model=ledger.effective_model,
            provider_success_path=self._derive_provider_success_path(ledger),
            used_mock_fallback=ledger.used_mock_fallback,
            fallback_reason=ledger.fallback_reason,
            elapsed_ms=ledger.elapsed_ms,
            event_count=len(ledger.events),
            artifact_count=artifact_count,
            available_actions=self._derive_available_actions(ledger),
            created_at=ledger.created_at,
            updated_at=ledger.updated_at,
        )

    def _derive_task_run_status(self, ledger: ResearchLedger) -> str:
        if ledger.current_state == "queued":
            return "queued"
        if ledger.current_state == "cancelled":
            return "cancelled"
        if ledger.current_state == "failed":
            return "failed"
        if ledger.current_state == "awaiting_review":
            return "awaiting_review"
        if ledger.current_state == "completed":
            return "completed"
        return "running"

    def _derive_artifact_count(self, ledger: ResearchLedger) -> int:
        if ledger.current_state not in TERMINAL_RUN_STATES:
            return 0
        artifact_count = len(ledger.artifacts)
        if artifact_count == 0:
            artifact_count = len(ledger.final_artifacts)
        return artifact_count

    def _derive_provider_success_path(self, ledger: ResearchLedger) -> str | None:
        if ledger.effective_runtime_mode != "agents_sdk" or ledger.used_mock_fallback:
            return None
        if ledger.current_state not in {"completed", "awaiting_review"}:
            return None
        provider_paths = [
            value.get("path")
            for key, value in ledger.repaired_outputs.items()
            if key.endswith(":provider_path") and isinstance(value, dict)
        ]
        if any(path == "plain_json_fallback" for path in provider_paths):
            return "plain_json_fallback"
        if any(path == "structured" for path in provider_paths):
            return "structured"
        return None

    def _derive_available_actions(self, ledger: ResearchLedger) -> list[str]:
        status_value = self._derive_task_run_status(ledger)
        actions: list[str] = []
        if status_value in {"queued", "running"}:
            actions.append("cancel")
        if status_value in {"completed", "cancelled", "failed", "awaiting_review"}:
            actions.append("retry")
        if status_value == "awaiting_review":
            actions.extend(["review_accept", "review_reject", "review_annotate"])
        return actions

    def _build_checkpoint_callback(self, run_id: str):
        def _callback(ledger: ResearchLedger) -> None:
            self.repository.update(ledger)
            self._abort_if_cancelled(run_id, ledger)

        return _callback

    def _abort_if_cancelled(self, run_id: str, ledger: ResearchLedger) -> None:
        with self._background_lock:
            handle = self._background_runs.get(run_id)
            cancel_requested = bool(handle and handle.cancel_requested)
            cancel_note = handle.cancel_note if handle is not None else None
        if ledger.current_state == "cancelled":
            raise TaskCancelledError(ledger.result_summary or cancel_note or "Task cancelled by operator.")
        if cancel_requested:
            raise TaskCancelledError(cancel_note or "Task cancelled by operator.")

    def _build_retry_request(self, ledger: ResearchLedger) -> AgentTaskCreateRequest:
        new_run_id = f"run-{uuid4().hex[:12]}"
        new_session_id = f"{ledger.session_id}-retry-{uuid4().hex[:6]}"
        payload = dict(ledger.request_payload or {})
        payload["_parent_run_id"] = ledger.run_id
        return AgentTaskCreateRequest(
            task_type=ledger.task_type or "research_plan",
            objective=ledger.request_objective or ledger.research_question,
            payload=payload,
            task_id=new_run_id,
            session_id=new_session_id,
            requested_by="user",
            priority="normal",
            constraints=list(ledger.request_constraints),
            dry_run=False,
        )

    def _default_review_note(self, decision: str) -> str:
        if decision == "accept":
            return "人工审核已通过该任务。"
        if decision == "reject":
            return "人工审核已驳回该任务。"
        return "已添加人工审核备注。"

    def _default_objective_for(self, task_type: str) -> str:
        defaults = {
            "competition_recommendation": "Generate grounded competition recommendations for the current student profile.",
            "competition_eligibility_check": "Evaluate whether the current student profile should join the target competition.",
            "competition_timeline_plan": "Build a reverse timeline plan for the target competition deadline.",
            "research_plan": "Run the legacy research runtime path.",
        }
        return defaults.get(task_type, "Run an agent task for the current competition assistant request.")
