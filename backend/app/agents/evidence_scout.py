from datetime import datetime, timezone
from typing import List

from app.schemas.research_runtime import AgentTaskEnvelope, EvidenceRecord, ResearchLedger, SourceRecord


class EvidenceScoutAgent:
    name = "evidence-scout"

    # Phase 3: replace deterministic evidence fabrication with real retrieval/extraction.
    def run(self, task: AgentTaskEnvelope, ledger: ResearchLedger, trend_result: dict) -> dict:
        timestamp = datetime.now(timezone.utc)
        directions: List[str] = trend_result["directions"]
        sources: List[SourceRecord] = []
        evidence_items: List[EvidenceRecord] = []

        for index, direction in enumerate(directions, start=1):
            source_id = f"{task.task_id}-source-{index}"
            source = SourceRecord(
                source_id=source_id,
                source_type="note",
                title=f"{direction} 的 mock 来源",
                locator=f"mock://research-runtime/{task.task_id}/source/{index}",
                credibility="medium",
                captured_by=self.name,
                tags=["mock", "phase2", "offline"],
            )
            sources.append(source)

            for sub_index in range(1, 3):
                evidence_id = f"{task.task_id}-evidence-{index}-{sub_index}"
                evidence_items.append(
                    EvidenceRecord(
                        evidence_id=evidence_id,
                        source_id=source_id,
                        claim=f"{direction} 需要可复现的结构化输入输出。",
                        excerpt=f"Mock evidence {sub_index} for {direction}：优先固定契约、Ledger 写回与测试路径。",
                        captured_by=self.name,
                        captured_at=timestamp,
                        related_task_id=task.task_id,
                    )
                )

        return {
            "agent": self.name,
            "sources": sources,
            "evidence": evidence_items,
            "notes": [f"基于 {len(directions)} 个方向生成了 {len(evidence_items)} 条 mock evidence。"],
        }