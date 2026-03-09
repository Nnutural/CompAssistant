from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable, Iterable, Mapping

from pydantic import BaseModel, Field

from app.agents.orchestrator import ResearchOrchestrator
from app.agents.output_repair import repair_output_to_model
from app.agents.output_validation import validate_output_against_model
from app.agents.run_state import (
    mark_review_required,
    record_artifact,
    record_issue,
    record_output,
    transition_state,
)
from app.schemas.research_runtime import (
    AgentResult,
    AgentTaskEnvelope,
    ArtifactItem,
    CompetitionEligibilityArtifact,
    CompetitionRecommendationArtifact,
    CompetitionTimelineArtifact,
    EvidenceRecord,
    FindingItem,
    LedgerTaskEntry,
    ResearchLedger,
    SourceRecord,
)

logger = logging.getLogger("uvicorn.error")

COMPETITION_TASK_MODELS: dict[str, type[BaseModel]] = {
    "competition_recommendation": CompetitionRecommendationArtifact,
    "competition_eligibility_check": CompetitionEligibilityArtifact,
    "competition_timeline_plan": CompetitionTimelineArtifact,
}


class ManagerAgentOutput(BaseModel):
    summary: str
    follow_up_items: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


def process_output_stage(
    *,
    ledger: ResearchLedger,
    stage: str,
    raw_output: Any,
    output_model: type[BaseModel],
    agent_name: str,
) -> tuple[BaseModel, bool, str | None]:
    record_output(ledger, stage=stage, payload=raw_output, repaired=False)
    repair_result = repair_output_to_model(raw_output, output_model)

    for parse_error in repair_result.parse_errors:
        record_issue(
            ledger,
            stage=stage,
            kind="parse_error",
            message=parse_error,
            agent=agent_name,
        )
    for warning in repair_result.warnings:
        record_issue(
            ledger,
            stage=stage,
            kind="repair_warning",
            message=warning,
            agent=agent_name,
        )

    if repair_result.repaired_output is not None:
        record_output(ledger, stage=stage, payload=repair_result.repaired_output, repaired=True)

    validation = validate_output_against_model(
        repair_result.repaired_output if repair_result.repaired_output is not None else repair_result.extracted_output,
        output_model,
    )
    for validation_error in validation.validation_errors:
        record_issue(
            ledger,
            stage=stage,
            kind="validation_error",
            message=validation_error,
            agent=agent_name,
        )
    if validation.review_required and validation.review_message:
        record_issue(
            ledger,
            stage=stage,
            kind="repair_warning",
            message=validation.review_message,
            agent=agent_name,
        )
    if validation.validated_output is None:
        raise RuntimeError(f"{agent_name} produced invalid output for {output_model.__name__}.")
    return validation.validated_output, validation.review_required, validation.review_message


class ResearchResultAssembler:
    def apply_pipeline(
        self,
        *,
        task: AgentTaskEnvelope,
        ledger: ResearchLedger,
        pipeline: Mapping[str, Any],
        started_at: datetime,
        completed_at: datetime,
        runtime_label: str,
        summary: str,
        follow_up_items: Iterable[str] | None = None,
        blockers: Iterable[str] | None = None,
        runtime_metadata: Mapping[str, Any] | None = None,
    ) -> tuple[AgentResult, ResearchLedger]:
        self._append_legacy_task_history(ledger, task, pipeline, started_at, completed_at)
        self._merge_sources(ledger, pipeline.get("evidence", {}).get("sources", []))
        self._merge_evidence(ledger, pipeline.get("evidence", {}).get("evidence", []))
        self._append_notes(ledger, pipeline)
        self._append_runtime_metadata(ledger, runtime_metadata or {})

        artifact = self._build_artifact(task, ledger, runtime_label)
        if not any(item.ref == artifact.ref for item in ledger.final_artifacts):
            ledger.final_artifacts.append(artifact)
        ledger.result_status = "completed"
        ledger.result_summary = summary
        ledger.follow_up_items = list(follow_up_items or [])
        ledger.blockers = list(blockers or [])
        ledger.finding_count = len(list(pipeline.get("critic", {}).get("findings", [])))
        ledger.updated_at = completed_at

        result = AgentResult(
            contract_version="1.0",
            task_id=task.task_id,
            produced_by="manager",
            status="completed",
            summary=summary,
            findings=self._coerce_findings(pipeline.get("critic", {}).get("findings", [])),
            artifacts=[artifact],
            follow_up_items=list(follow_up_items or []),
            blockers=list(blockers or []),
            completed_at=completed_at,
        )
        return result, ledger

    def apply_competition_output(
        self,
        *,
        task: AgentTaskEnvelope,
        ledger: ResearchLedger,
        specialist_name: str,
        validated_output: BaseModel,
        started_at: datetime,
        completed_at: datetime,
        runtime_label: str,
        review_required: bool,
        review_message: str | None,
        follow_up_items: Iterable[str] | None = None,
        blockers: Iterable[str] | None = None,
        runtime_metadata: Mapping[str, Any] | None = None,
    ) -> tuple[AgentResult, ResearchLedger]:
        self._append_competition_task_history(
            ledger,
            task,
            specialist_name,
            validated_output,
            started_at,
            completed_at,
        )
        self._append_runtime_metadata(ledger, runtime_metadata or {})

        artifact = self._build_artifact(task, ledger, runtime_label)
        if not any(item.ref == artifact.ref for item in ledger.final_artifacts):
            ledger.final_artifacts.append(artifact)
        record_artifact(
            ledger,
            artifact_id=f"{task.task_id}:artifact",
            artifact_type=task.task_type,
            title=f"{task.task_type} artifact",
            payload=validated_output,
        )
        ledger.result_status = "needs_human" if review_required else "completed"
        ledger.result_summary = _build_competition_summary(validated_output)
        ledger.updated_at = completed_at

        final_follow_up_items = list(follow_up_items or [])
        if review_required and review_message:
            final_follow_up_items.append(review_message)
        ledger.follow_up_items = list(final_follow_up_items)
        ledger.blockers = list(blockers or [])
        ledger.finding_count = len(_build_competition_findings(validated_output))
        result = AgentResult(
            contract_version="1.0",
            task_id=task.task_id,
            produced_by="manager",
            status="needs_human" if review_required else "completed",
            summary=_build_competition_summary(validated_output),
            findings=_build_competition_findings(validated_output),
            artifacts=[artifact],
            follow_up_items=final_follow_up_items,
            blockers=list(blockers or []),
            completed_at=completed_at,
        )
        return result, ledger

    def _append_legacy_task_history(
        self,
        ledger: ResearchLedger,
        task: AgentTaskEnvelope,
        pipeline: Mapping[str, Any],
        started_at: datetime,
        completed_at: datetime,
    ) -> None:
        trend_count = len(list(pipeline.get("trend", {}).get("directions", [])))
        evidence_count = len(list(pipeline.get("evidence", {}).get("evidence", [])))
        task_entries = [
            LedgerTaskEntry(
                task_id=f"{task.task_id}:trend-scout",
                agent="trend-scout",
                status="completed",
                summary=f"Generated {trend_count} candidate directions.",
                started_at=started_at,
                completed_at=completed_at,
            ),
            LedgerTaskEntry(
                task_id=f"{task.task_id}:evidence-scout",
                agent="evidence-scout",
                status="completed",
                summary=f"Generated {evidence_count} evidence records.",
                started_at=started_at,
                completed_at=completed_at,
            ),
            LedgerTaskEntry(
                task_id=f"{task.task_id}:critic",
                agent="critic",
                status="completed",
                summary="Produced novelty, feasibility, and risk notes.",
                started_at=started_at,
                completed_at=completed_at,
            ),
            LedgerTaskEntry(
                task_id=task.task_id,
                agent="manager",
                status="completed",
                summary="Aggregated specialist outputs and updated the Research Ledger.",
                started_at=started_at,
                completed_at=completed_at,
            ),
        ]
        ledger.task_history.extend(task_entries)

    def _append_competition_task_history(
        self,
        ledger: ResearchLedger,
        task: AgentTaskEnvelope,
        specialist_name: str,
        validated_output: BaseModel,
        started_at: datetime,
        completed_at: datetime,
    ) -> None:
        specialist_summary = _build_competition_summary(validated_output)
        ledger.task_history.extend(
            [
                LedgerTaskEntry(
                    task_id=f"{task.task_id}:{specialist_name}",
                    agent=specialist_name,
                    status="completed",
                    summary=specialist_summary,
                    started_at=started_at,
                    completed_at=completed_at,
                ),
                LedgerTaskEntry(
                    task_id=task.task_id,
                    agent="manager",
                    status="completed",
                    summary=f"Completed {task.task_type} using {specialist_name}.",
                    started_at=started_at,
                    completed_at=completed_at,
                ),
            ]
        )

    def _merge_sources(self, ledger: ResearchLedger, sources: Iterable[Any]) -> None:
        known_ids = {item.source_id for item in ledger.source_registry}
        for source in self._coerce_sources(sources):
            if source.source_id not in known_ids:
                ledger.source_registry.append(source)
                known_ids.add(source.source_id)

    def _merge_evidence(self, ledger: ResearchLedger, evidence_items: Iterable[Any]) -> None:
        known_ids = {item.evidence_id for item in ledger.evidence_log}
        for evidence in self._coerce_evidence(evidence_items):
            if evidence.evidence_id not in known_ids:
                ledger.evidence_log.append(evidence)
                known_ids.add(evidence.evidence_id)

    def _append_notes(self, ledger: ResearchLedger, pipeline: Mapping[str, Any]) -> None:
        notes: list[str] = []
        for section_name in ("trend", "evidence", "critic"):
            section = pipeline.get(section_name, {})
            notes.extend([str(item) for item in section.get("notes", []) if str(item).strip()])
        for note in notes:
            if note not in ledger.synthesis_notes:
                ledger.synthesis_notes.append(note)

    def _append_runtime_metadata(self, ledger: ResearchLedger, runtime_metadata: Mapping[str, Any]) -> None:
        metadata_notes = []
        mode = runtime_metadata.get("mode")
        if mode:
            metadata_notes.append(f"runtime mode: {mode}")
        model = runtime_metadata.get("model")
        if model:
            metadata_notes.append(f"runtime model: {model}")
        base_url = runtime_metadata.get("base_url")
        if base_url:
            metadata_notes.append(f"runtime base url: {base_url}")
        if "tracing_enabled" in runtime_metadata:
            metadata_notes.append(
                f"tracing enabled: {str(bool(runtime_metadata.get('tracing_enabled'))).lower()}"
            )
        if "used_mock_fallback" in runtime_metadata:
            metadata_notes.append(
                f"used mock fallback: {str(bool(runtime_metadata.get('used_mock_fallback'))).lower()}"
            )
        fallback_reason = runtime_metadata.get("fallback_reason")
        if fallback_reason:
            metadata_notes.append(f"fallback reason: {fallback_reason}")
        manager_session_id = runtime_metadata.get("manager_session_id")
        if manager_session_id:
            metadata_notes.append(f"manager session id: {manager_session_id}")
        manager_trace_id = runtime_metadata.get("manager_trace_id")
        if manager_trace_id:
            metadata_notes.append(f"manager trace id: {manager_trace_id}")

        specialist_session_ids = runtime_metadata.get("specialist_session_ids", {}) or {}
        for name, session_id in specialist_session_ids.items():
            metadata_notes.append(f"{name} session id: {session_id}")

        specialist_trace_ids = runtime_metadata.get("specialist_trace_ids", {}) or {}
        for name, trace_id in specialist_trace_ids.items():
            metadata_notes.append(f"{name} trace id: {trace_id}")

        for note in metadata_notes:
            if note not in ledger.synthesis_notes:
                ledger.synthesis_notes.append(note)

        if model:
            ledger.model = model
        if base_url:
            ledger.base_url = base_url
        if "used_mock_fallback" in runtime_metadata:
            ledger.used_mock_fallback = bool(runtime_metadata.get("used_mock_fallback"))
        if fallback_reason:
            ledger.fallback_reason = str(fallback_reason)

    def _build_artifact(self, task: AgentTaskEnvelope, ledger: ResearchLedger, runtime_label: str) -> ArtifactItem:
        return ArtifactItem(
            kind="report",
            ref=f"{runtime_label}://research-runtime/{ledger.ledger_id}/result/{task.task_id}",
            title=f"Research runtime result ({runtime_label})",
        )

    def _coerce_sources(self, sources: Iterable[Any]) -> list[SourceRecord]:
        return [item if isinstance(item, SourceRecord) else SourceRecord.model_validate(item) for item in sources]

    def _coerce_evidence(self, evidence_items: Iterable[Any]) -> list[EvidenceRecord]:
        return [item if isinstance(item, EvidenceRecord) else EvidenceRecord.model_validate(item) for item in evidence_items]

    def _coerce_findings(self, findings: Iterable[Any]) -> list[FindingItem]:
        return [item if isinstance(item, FindingItem) else FindingItem.model_validate(item) for item in findings]


class ResearchRuntimeManager:
    def __init__(self, orchestrator: ResearchOrchestrator | None = None, assembler: ResearchResultAssembler | None = None):
        self.orchestrator = orchestrator or ResearchOrchestrator()
        self.assembler = assembler or ResearchResultAssembler()

    def run(
        self,
        task: AgentTaskEnvelope,
        ledger: ResearchLedger,
        checkpoint_callback: Callable[[ResearchLedger], None] | None = None,
        abort_if_requested: Callable[[ResearchLedger], None] | None = None,
    ) -> tuple[AgentResult, ResearchLedger]:
        started_at_perf = perf_counter()
        logger.info("[research-runtime] mock manager start task_id=%s ledger_id=%s", task.task_id, ledger.ledger_id)
        started_at = datetime.now(timezone.utc)
        _abort_if_requested(ledger, abort_if_requested)
        transition_state(
            ledger,
            "retrieving_local_context",
            actor="mock-manager",
            message="正在读取本地竞赛数据、规则与模板。",
        )
        _emit_checkpoint(ledger, checkpoint_callback)
        _abort_if_requested(ledger, abort_if_requested)
        transition_state(
            ledger,
            "reasoning",
            actor="mock-manager",
            message="正在执行 mock specialist 流程。",
        )
        _emit_checkpoint(ledger, checkpoint_callback)
        _abort_if_requested(ledger, abort_if_requested)
        pipeline = self.orchestrator.run(task, ledger)
        completed_at = datetime.now(timezone.utc)
        _abort_if_requested(ledger, abort_if_requested)

        if task.task_type in COMPETITION_TASK_MODELS:
            transition_state(
                ledger,
                "validating_output",
                actor="mock-manager",
                message="正在修复并校验 specialist 输出。",
            )
            _emit_checkpoint(ledger, checkpoint_callback)
            _abort_if_requested(ledger, abort_if_requested)
            specialist_name = str(pipeline["specialist_name"])
            validated_output, review_required, review_message = process_output_stage(
                ledger=ledger,
                stage=specialist_name,
                raw_output=pipeline["specialist_output"],
                output_model=COMPETITION_TASK_MODELS[task.task_type],
                agent_name=specialist_name,
            )
            record_output(
                ledger,
                stage="final",
                payload=validated_output.model_dump(mode="json", exclude_none=True),
                repaired=True,
            )
            _emit_checkpoint(ledger, checkpoint_callback)
            _abort_if_requested(ledger, abort_if_requested)
            follow_up_items = [
                "当前结果完全基于本地 competitions 数据、规则和模板生成。",
            ]
            result, updated_ledger = self.assembler.apply_competition_output(
                task=task,
                ledger=ledger,
                specialist_name=specialist_name,
                validated_output=validated_output,
                started_at=started_at,
                completed_at=completed_at,
                runtime_label="mock",
                review_required=review_required,
                review_message=review_message,
                follow_up_items=follow_up_items,
                blockers=[],
                runtime_metadata={"mode": "mock"},
            )
            if review_required:
                mark_review_required(
                    updated_ledger,
                    actor="mock-manager",
                    message=review_message or "Output requires manual review.",
                )
            _emit_checkpoint(updated_ledger, checkpoint_callback)
            _abort_if_requested(updated_ledger, abort_if_requested)
            logger.info(
                "[research-runtime] mock manager completed competition task_id=%s ledger_id=%s status=%s elapsed_ms=%.2f",
                task.task_id,
                ledger.ledger_id,
                result.status,
                (perf_counter() - started_at_perf) * 1000,
            )
            return result, updated_ledger

        record_output(ledger, stage="legacy_pipeline", payload=pipeline, repaired=False)
        transition_state(
            ledger,
            "validating_output",
            actor="mock-manager",
            message="正在记录 legacy research pipeline 输出。",
        )
        record_output(ledger, stage="legacy_pipeline", payload=pipeline, repaired=True)
        _emit_checkpoint(ledger, checkpoint_callback)
        _abort_if_requested(ledger, abort_if_requested)

        direction_count = len(list(pipeline.get("trend", {}).get("directions", [])))
        evidence_count = len(list(pipeline.get("evidence", {}).get("evidence", [])))
        summary = (
            "Manager completed the offline mock research runtime: "
            f"generated {direction_count} candidate directions, "
            f"captured {evidence_count} evidence records, and produced a structured critique."
        )
        follow_up_items = [
            "Legacy research_plan remains compatible but is no longer the primary competition-assistant demo path.",
            "Current result still uses the older research-style mock specialists.",
        ]
        result = self.assembler.apply_pipeline(
            task=task,
            ledger=ledger,
            pipeline=pipeline,
            started_at=started_at,
            completed_at=completed_at,
            runtime_label="mock",
            summary=summary,
            follow_up_items=follow_up_items,
            blockers=[],
            runtime_metadata={"mode": "mock"},
        )
        logger.info(
            "[research-runtime] mock manager completed legacy task_id=%s ledger_id=%s directions=%s evidence=%s findings=%s elapsed_ms=%.2f",
            task.task_id,
            ledger.ledger_id,
            direction_count,
            evidence_count,
            len(result[0].findings),
            (perf_counter() - started_at_perf) * 1000,
        )
        return result


def _emit_checkpoint(
    ledger: ResearchLedger,
    checkpoint_callback: Callable[[ResearchLedger], None] | None,
) -> None:
    if checkpoint_callback is not None:
        checkpoint_callback(ledger)


def _abort_if_requested(
    ledger: ResearchLedger,
    abort_if_requested: Callable[[ResearchLedger], None] | None,
) -> None:
    if abort_if_requested is not None:
        abort_if_requested(ledger)


def _build_competition_summary(validated_output: BaseModel) -> str:
    if isinstance(validated_output, CompetitionRecommendationArtifact):
        top_names = [item.competition_name for item in validated_output.recommendations[:3]]
        return f"Generated {len(validated_output.recommendations)} competition recommendations: {', '.join(top_names)}."
    if isinstance(validated_output, CompetitionEligibilityArtifact):
        return (
            f"{validated_output.competition_name} eligibility result: "
            f"{validated_output.eligibility_label}."
        )
    if isinstance(validated_output, CompetitionTimelineArtifact):
        return (
            f"Built a timeline for {validated_output.competition_name} with "
            f"{len(validated_output.milestones)} milestones."
        )
    return "Generated a structured competition runtime artifact."


def _build_competition_findings(validated_output: BaseModel) -> list[FindingItem]:
    if isinstance(validated_output, CompetitionRecommendationArtifact):
        findings = []
        for index, item in enumerate(validated_output.recommendations[:3], start=1):
            findings.append(
                FindingItem(
                    finding_id=f"recommendation-{index}",
                    claim=f"{item.competition_name} is a strong candidate with score {item.match_score}.",
                    evidence_refs=[],
                    confidence="medium",
                )
            )
        return findings
    if isinstance(validated_output, CompetitionEligibilityArtifact):
        return [
            FindingItem(
                finding_id=f"eligibility-{validated_output.competition_id}",
                claim=(
                    f"{validated_output.competition_name} is assessed as "
                    f"{validated_output.eligibility_label}."
                ),
                evidence_refs=[],
                confidence="high",
            )
        ]
    if isinstance(validated_output, CompetitionTimelineArtifact):
        return [
            FindingItem(
                finding_id=f"timeline-{validated_output.competition_id}",
                claim=(
                    f"{validated_output.competition_name} timeline contains "
                    f"{len(validated_output.milestones)} milestones."
                ),
                evidence_refs=[],
                confidence="medium",
            )
        ]
    return []
