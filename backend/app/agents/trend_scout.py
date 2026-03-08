from app.schemas.research_runtime import AgentTaskEnvelope, ResearchLedger


class TrendScoutAgent:
    name = "trend-scout"

    # Phase 3: replace deterministic direction generation with a real agent call.
    def run(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> dict:
        topic = str(task.payload.get("topic") or ledger.topic or task.objective)
        objective = task.objective.strip()
        directions = [
            f"{topic}的编排链路设计",
            f"{topic}的证据沉淀与Ledger写回",
            f"{topic}的离线验证与演示路径",
        ]
        return {
            "agent": self.name,
            "directions": directions,
            "notes": [
                f"围绕主题“{topic}”生成了 3 个候选子方向。",
                f"目标上下文为：{objective}",
            ],
        }