from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Iterable, Optional
from uuid import uuid4

from app.agents.manager import ResearchRuntimeManager
from app.agents.run_state import (
    mark_completed,
    mark_failed,
    mark_fallback,
    mark_review_required,
    reset_run_tracking,
    transition_state,
)
from app.agents.sdk_runtime import AgentsSDKResearchRuntime
from app.core.config import Settings, settings
from app.repositories.ledger_repository import LedgerRepository
from app.schemas.agent_tasks import (
    AgentTaskArtifactItem,
    AgentTaskArtifactsResponse,
    AgentTaskCreateRequest,
    AgentTaskEventItem,
    AgentTaskEventsResponse,
    AgentTaskResultSummary,
    AgentTaskStatusResponse,
)
from app.schemas.research_runtime import AgentResult, AgentTaskEnvelope, ArtifactItem, ResearchLedger, ResearchScope

logger = logging.getLogger("uvicorn.error")


class ResearchRuntimeService:
    def __init__(
        self,
        repository: Optional[LedgerRepository] = None,
        manager: Optional[ResearchRuntimeManager] = None,
        sdk_runtime: Optional[AgentsSDKResearchRuntime] = None,
        settings_obj: Optional[Settings] = None,
        runtime_mode: Optional[str] = None,
        strict_mode: Optional[bool] = None,
    ):
        self.settings = settings_obj or settings
        self.repository = repository or LedgerRepository()
        self.manager = manager or ResearchRuntimeManager()
        self.sdk_runtime = sdk_runtime
        self.runtime_mode = runtime_mode or self.settings.research_runtime_mode
        self.strict_mode = self.settings.research_runtime_strict_mode if strict_mode is None else strict_mode

    def run_task(self, task: AgentTaskEnvelope) -> AgentResult:
        started_at = perf_counter()
        logger.info(
            "[research-runtime] run_task start task_id=%s session_id=%s runtime_mode=%s strict_mode=%s",
            task.task_id,
            task.session_id,
            self.runtime_mode,
            self.strict_mode,
        )
        ledger = self._load_or_create_ledger(task)
        self._prepare_run(ledger, task)

        try:
            result, updated_ledger = self._run_runtime(task, ledger)
            review_required = updated_ledger.current_state == "awaiting_review" or result.status == "needs_human"
            review_message = result.follow_up_items[-1] if result.follow_up_items else "Run requires manual review."
            transition_state(
                updated_ledger,
                "persisting_artifacts",
                actor="service",
                message="Persisting run artifacts and ledger state.",
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
                    message="Run completed and persisted.",
                    elapsed_ms=elapsed_ms,
                )
            self.repository.update(updated_ledger)
        except Exception as exc:
            elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
            ledger.result_status = "blocked"
            ledger.result_summary = f"Run failed: {exc}"
            ledger.blockers = [str(exc)]
            mark_failed(
                ledger,
                stage=ledger.current_state or "planning",
                actor="service",
                message=f"Run failed: {exc}",
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
        try:
            self.run_task(envelope)
        except Exception:
            pass

        status = self.get_task_status(run_id)
        if status is None:
            raise RuntimeError(f"Unable to resolve run status for run_id={run_id}")
        return status

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
        items: list[AgentTaskArtifactItem] = [
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
        if not items:
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

    def _run_runtime(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> tuple[AgentResult, ResearchLedger]:
        runtime_started_at = perf_counter()
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
                result, updated_ledger = runtime.run(task, ledger)
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
                mark_fallback(ledger, reason=note, actor="service")
                return self._run_mock_with_note(task, ledger, note)

        logger.info(
            "[research-runtime] selecting mock runtime task_id=%s ledger_id=%s",
            task.task_id,
            ledger.ledger_id,
        )
        result, updated_ledger = self.manager.run(task, ledger)
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
        logger.info(
            "[research-runtime] falling back to mock runtime task_id=%s ledger_id=%s reason=%s",
            task.task_id,
            ledger.ledger_id,
            note,
        )
        result, updated_ledger = self.manager.run(task, ledger)
        fallback_note = f"Returned mock-derived result because {note}"
        if fallback_note not in result.follow_up_items:
            result.follow_up_items.insert(0, fallback_note)
        if note not in updated_ledger.synthesis_notes:
            updated_ledger.synthesis_notes.append(note)
        updated_ledger.used_mock_fallback = True
        updated_ledger.fallback_reason = note
        fallback_metadata = [
            f"runtime model: {self.settings.openai_default_model}",
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

    def _prepare_run(self, ledger: ResearchLedger, task: AgentTaskEnvelope) -> None:
        model = self.settings.openai_default_model if self.runtime_mode == "agents_sdk" else "mock"
        base_url = self.settings.openai_base_url if self.runtime_mode == "agents_sdk" else None
        reset_run_tracking(ledger, task, model=model, base_url=base_url)
        transition_state(ledger, "received", actor="service", message="Task received by runtime service.")
        transition_state(ledger, "planning", actor="service", message="Planning runtime path and state machine.")
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
            scope=scope,
            hypotheses=self._coerce_str_list(task.payload.get("hypotheses"), default=[]),
            task_history=[],
            source_registry=[],
            evidence_log=[],
            synthesis_notes=[],
            final_artifacts=[],
            open_questions=self._coerce_str_list(task.payload.get("open_questions"), default=[]),
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

    def _resolve_ledger_id(self, task: AgentTaskEnvelope) -> str:
        payload_ledger_id = task.payload.get("ledger_id")
        if isinstance(payload_ledger_id, str) and payload_ledger_id.strip():
            return payload_ledger_id.strip()
        return f"ledger-{task.session_id}"

    def _coerce_str_list(self, value, default: Iterable[str]) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return list(default)

    def _to_repo_relative(self, path) -> str:
        repo_root = path.resolve().parents[3]
        return path.resolve().relative_to(repo_root).as_posix()

    def _build_task_status_response(self, ledger: ResearchLedger, run_id: str) -> AgentTaskStatusResponse:
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
            used_mock_fallback=ledger.used_mock_fallback,
            fallback_reason=ledger.fallback_reason,
            elapsed_ms=ledger.elapsed_ms,
            event_count=len(ledger.events),
            artifact_count=max(len(ledger.artifacts), len(ledger.final_artifacts)),
            created_at=ledger.created_at,
            updated_at=ledger.updated_at,
        )

    def _derive_task_run_status(self, ledger: ResearchLedger) -> str:
        if ledger.current_state == "failed":
            return "failed"
        if ledger.current_state == "awaiting_review":
            return "awaiting_review"
        if ledger.current_state == "completed":
            return "completed"
        return "running"

    def _default_objective_for(self, task_type: str) -> str:
        defaults = {
            "competition_recommendation": "Generate grounded competition recommendations for the current student profile.",
            "competition_eligibility_check": "Evaluate whether the current student profile should join the target competition.",
            "competition_timeline_plan": "Build a reverse timeline plan for the target competition deadline.",
            "research_plan": "Run the legacy research runtime path.",
        }
        return defaults.get(task_type, "Run an agent task for the current competition assistant request.")
