from app.schemas.research_runtime import AgentTaskEnvelope, FindingItem, ResearchLedger


class CriticAgent:
    name = "critic"

    # Phase 3: replace heuristic critique with real model-based assessment.
    def run(self, task: AgentTaskEnvelope, ledger: ResearchLedger, trend_result: dict, evidence_result: dict) -> dict:
        evidence_refs = [item.evidence_id for item in evidence_result["evidence"][:3]]
        novelty_note = "novelty：把运行时契约、Ledger 写回和 API 演示固定在同一条离线链路中。"
        feasibility_note = "feasibility：当前方案仅依赖本地 JSON 持久化与 FastAPI，落地成本低。"
        risk_note = "risk：当前全部为 mock agent，后续接入真实 Agents SDK 时需要补充调度与错误恢复。"

        findings = [
            FindingItem(
                finding_id=f"{task.task_id}-finding-1",
                claim="当前离线运行时骨架适合作为 Phase 2 演示基线。",
                evidence_refs=evidence_refs,
                confidence="high",
            ),
            FindingItem(
                finding_id=f"{task.task_id}-finding-2",
                claim="Research Ledger 可以作为任务轨迹、来源和证据的统一写回容器。",
                evidence_refs=evidence_refs,
                confidence="high",
            ),
        ]

        return {
            "agent": self.name,
            "assessment": {
                "novelty": novelty_note,
                "feasibility": feasibility_note,
                "risk": risk_note,
            },
            "findings": findings,
            "notes": [novelty_note, feasibility_note, risk_note],
        }