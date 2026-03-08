from datetime import datetime, timezone

from app.agents.orchestrator import ResearchOrchestrator
from app.schemas.research_runtime import (
    AgentResult,
    AgentTaskEnvelope,
    ArtifactItem,
    LedgerTaskEntry,
    ResearchLedger,
)


class ResearchRuntimeManager:
    def __init__(self, orchestrator: ResearchOrchestrator | None = None):
        self.orchestrator = orchestrator or ResearchOrchestrator()

    # Phase 3: replace this orchestration manager with real SDK-based planning and delegation.
    def run(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> tuple[AgentResult, ResearchLedger]:
        started_at = datetime.now(timezone.utc)
        pipeline = self.orchestrator.run(task, ledger)
        completed_at = datetime.now(timezone.utc)

        self._append_task_history(ledger, task, pipeline, started_at, completed_at)
        self._merge_sources(ledger, pipeline["evidence"]["sources"])
        self._merge_evidence(ledger, pipeline["evidence"]["evidence"])
        self._append_notes(ledger, pipeline)
        artifact = self._build_artifact(task, ledger)
        if not any(item.ref == artifact.ref for item in ledger.final_artifacts):
            ledger.final_artifacts.append(artifact)
        ledger.updated_at = completed_at

        summary = (
            f"Manager 完成离线 mock research runtime 运行：生成 {len(pipeline['trend']['directions'])} 个候选方向，"
            f"沉淀 {len(pipeline['evidence']['evidence'])} 条证据，并输出批判性总结。"
        )
        result = AgentResult(
            contract_version="1.0",
            task_id=task.task_id,
            produced_by="manager",
            status="completed",
            summary=summary,
            findings=pipeline["critic"]["findings"],
            artifacts=[artifact],
            follow_up_items=[
                "Phase 3 可将 mock agents 替换为真实 Agents SDK 编排。",
                "如需持久化更多运行元数据，可扩展 Ledger 字段而不改变契约语义。",
            ],
            completed_at=completed_at,
        )
        return result, ledger

    def _append_task_history(self, ledger: ResearchLedger, task: AgentTaskEnvelope, pipeline: dict, started_at: datetime, completed_at: datetime) -> None:
        task_entries = [
            LedgerTaskEntry(
                task_id=f"{task.task_id}:trend-scout",
                agent="trend-scout",
                status="completed",
                summary=f"生成 {len(pipeline['trend']['directions'])} 个候选子方向。",
                started_at=started_at,
                completed_at=completed_at,
            ),
            LedgerTaskEntry(
                task_id=f"{task.task_id}:evidence-scout",
                agent="evidence-scout",
                status="completed",
                summary=f"生成 {len(pipeline['evidence']['evidence'])} 条 mock evidence。",
                started_at=started_at,
                completed_at=completed_at,
            ),
            LedgerTaskEntry(
                task_id=f"{task.task_id}:critic",
                agent="critic",
                status="completed",
                summary="输出 novelty、feasibility、risk 说明。",
                started_at=started_at,
                completed_at=completed_at,
            ),
            LedgerTaskEntry(
                task_id=task.task_id,
                agent="manager",
                status="completed",
                summary="汇总执行结果并写回 Research Ledger。",
                started_at=started_at,
                completed_at=completed_at,
            ),
        ]
        ledger.task_history.extend(task_entries)

    def _merge_sources(self, ledger: ResearchLedger, sources) -> None:
        known_ids = {item.source_id for item in ledger.source_registry}
        for source in sources:
            if source.source_id not in known_ids:
                ledger.source_registry.append(source)
                known_ids.add(source.source_id)

    def _merge_evidence(self, ledger: ResearchLedger, evidence_items) -> None:
        known_ids = {item.evidence_id for item in ledger.evidence_log}
        for evidence in evidence_items:
            if evidence.evidence_id not in known_ids:
                ledger.evidence_log.append(evidence)
                known_ids.add(evidence.evidence_id)

    def _append_notes(self, ledger: ResearchLedger, pipeline: dict) -> None:
        notes = []
        notes.extend(pipeline["trend"].get("notes", []))
        notes.extend(pipeline["evidence"].get("notes", []))
        notes.extend(pipeline["critic"].get("notes", []))
        for note in notes:
            if note not in ledger.synthesis_notes:
                ledger.synthesis_notes.append(note)

    def _build_artifact(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> ArtifactItem:
        return ArtifactItem(
            kind="report",
            ref=f"mock://research-runtime/{ledger.ledger_id}/result/{task.task_id}",
            title="离线 mock research runtime 结果",
        )