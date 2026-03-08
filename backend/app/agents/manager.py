from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from pydantic import BaseModel, Field

from app.agents.orchestrator import ResearchOrchestrator
from app.schemas.research_runtime import (
    AgentResult,
    AgentTaskEnvelope,
    ArtifactItem,
    EvidenceRecord,
    FindingItem,
    LedgerTaskEntry,
    ResearchLedger,
    SourceRecord,
)


class ManagerAgentOutput(BaseModel):
    summary: str
    follow_up_items: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


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
        self._append_task_history(ledger, task, pipeline, started_at, completed_at)
        self._merge_sources(ledger, pipeline.get('evidence', {}).get('sources', []))
        self._merge_evidence(ledger, pipeline.get('evidence', {}).get('evidence', []))
        self._append_notes(ledger, pipeline)
        self._append_runtime_metadata(ledger, runtime_metadata or {})

        artifact = self._build_artifact(task, ledger, runtime_label)
        if not any(item.ref == artifact.ref for item in ledger.final_artifacts):
            ledger.final_artifacts.append(artifact)
        ledger.updated_at = completed_at

        result = AgentResult(
            contract_version='1.0',
            task_id=task.task_id,
            produced_by='manager',
            status='completed',
            summary=summary,
            findings=self._coerce_findings(pipeline.get('critic', {}).get('findings', [])),
            artifacts=[artifact],
            follow_up_items=list(follow_up_items or []),
            blockers=list(blockers or []),
            completed_at=completed_at,
        )
        return result, ledger

    def _append_task_history(
        self,
        ledger: ResearchLedger,
        task: AgentTaskEnvelope,
        pipeline: Mapping[str, Any],
        started_at: datetime,
        completed_at: datetime,
    ) -> None:
        trend_count = len(list(pipeline.get('trend', {}).get('directions', [])))
        evidence_count = len(list(pipeline.get('evidence', {}).get('evidence', [])))
        task_entries = [
            LedgerTaskEntry(
                task_id=f'{task.task_id}:trend-scout',
                agent='trend-scout',
                status='completed',
                summary=f'Generated {trend_count} candidate directions.',
                started_at=started_at,
                completed_at=completed_at,
            ),
            LedgerTaskEntry(
                task_id=f'{task.task_id}:evidence-scout',
                agent='evidence-scout',
                status='completed',
                summary=f'Generated {evidence_count} evidence records.',
                started_at=started_at,
                completed_at=completed_at,
            ),
            LedgerTaskEntry(
                task_id=f'{task.task_id}:critic',
                agent='critic',
                status='completed',
                summary='Produced novelty, feasibility, and risk notes.',
                started_at=started_at,
                completed_at=completed_at,
            ),
            LedgerTaskEntry(
                task_id=task.task_id,
                agent='manager',
                status='completed',
                summary='Aggregated specialist outputs and updated the Research Ledger.',
                started_at=started_at,
                completed_at=completed_at,
            ),
        ]
        ledger.task_history.extend(task_entries)

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
        for section_name in ('trend', 'evidence', 'critic'):
            section = pipeline.get(section_name, {})
            notes.extend([str(item) for item in section.get('notes', []) if str(item).strip()])
        for note in notes:
            if note not in ledger.synthesis_notes:
                ledger.synthesis_notes.append(note)

    def _append_runtime_metadata(self, ledger: ResearchLedger, runtime_metadata: Mapping[str, Any]) -> None:
        metadata_notes = []
        mode = runtime_metadata.get('mode')
        if mode:
            metadata_notes.append(f'runtime mode: {mode}')
        manager_session_id = runtime_metadata.get('manager_session_id')
        if manager_session_id:
            metadata_notes.append(f'manager session id: {manager_session_id}')
        manager_trace_id = runtime_metadata.get('manager_trace_id')
        if manager_trace_id:
            metadata_notes.append(f'manager trace id: {manager_trace_id}')

        specialist_session_ids = runtime_metadata.get('specialist_session_ids', {}) or {}
        for name, session_id in specialist_session_ids.items():
            metadata_notes.append(f'{name} session id: {session_id}')

        specialist_trace_ids = runtime_metadata.get('specialist_trace_ids', {}) or {}
        for name, trace_id in specialist_trace_ids.items():
            metadata_notes.append(f'{name} trace id: {trace_id}')

        for note in metadata_notes:
            if note not in ledger.synthesis_notes:
                ledger.synthesis_notes.append(note)

    def _build_artifact(self, task: AgentTaskEnvelope, ledger: ResearchLedger, runtime_label: str) -> ArtifactItem:
        return ArtifactItem(
            kind='report',
            ref=f'{runtime_label}://research-runtime/{ledger.ledger_id}/result/{task.task_id}',
            title=f'Research runtime result ({runtime_label})',
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

    # Mock fallback manager. The real SDK-backed runtime is implemented in sdk_runtime.py.
    def run(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> tuple[AgentResult, ResearchLedger]:
        started_at = datetime.now(timezone.utc)
        pipeline = self.orchestrator.run(task, ledger)
        completed_at = datetime.now(timezone.utc)

        direction_count = len(list(pipeline.get('trend', {}).get('directions', [])))
        evidence_count = len(list(pipeline.get('evidence', {}).get('evidence', [])))
        summary = (
            'Manager completed the offline mock research runtime: '
            f'generated {direction_count} candidate directions, '
            f'captured {evidence_count} evidence records, and produced a structured critique.'
        )
        follow_up_items = [
            'Phase 3 can swap the mock specialists for a real OpenAI Agents SDK runtime while keeping the contracts stable.',
            'Phase 4 can add network-backed evidence collection without changing the API shape.',
        ]
        return self.assembler.apply_pipeline(
            task=task,
            ledger=ledger,
            pipeline=pipeline,
            started_at=started_at,
            completed_at=completed_at,
            runtime_label='mock',
            summary=summary,
            follow_up_items=follow_up_items,
            blockers=[],
            runtime_metadata={'mode': 'mock'},
        )
