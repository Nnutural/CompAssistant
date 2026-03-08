from app.agents.registry import MockAgentRegistry
from app.schemas.research_runtime import AgentTaskEnvelope, ResearchLedger


class ResearchOrchestrator:
    def __init__(self, registry: MockAgentRegistry | None = None):
        self.registry = registry or MockAgentRegistry()

    def run(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> dict:
        trend_result = self.registry.get("trend-scout").run(task, ledger)
        evidence_result = self.registry.get("evidence-scout").run(task, ledger, trend_result)
        critic_result = self.registry.get("critic").run(task, ledger, trend_result, evidence_result)
        return {
            "trend": trend_result,
            "evidence": evidence_result,
            "critic": critic_result,
        }