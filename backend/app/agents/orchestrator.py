import logging
from time import perf_counter

from app.agents.registry import MockAgentRegistry
from app.schemas.research_runtime import AgentTaskEnvelope, ResearchLedger

logger = logging.getLogger("uvicorn.error")


class ResearchOrchestrator:
    def __init__(self, registry: MockAgentRegistry | None = None):
        self.registry = registry or MockAgentRegistry()

    def run(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> dict:
        started_at = perf_counter()
        logger.info("[research-runtime] mock orchestrator trend-scout start task_id=%s", task.task_id)
        trend_started_at = perf_counter()
        trend_result = self.registry.get("trend-scout").run(task, ledger)
        logger.info(
            "[research-runtime] mock orchestrator trend-scout completed task_id=%s directions=%s elapsed_ms=%.2f",
            task.task_id,
            len(trend_result.get("directions", [])),
            (perf_counter() - trend_started_at) * 1000,
        )
        logger.info("[research-runtime] mock orchestrator evidence-scout start task_id=%s", task.task_id)
        evidence_started_at = perf_counter()
        evidence_result = self.registry.get("evidence-scout").run(task, ledger, trend_result)
        logger.info(
            "[research-runtime] mock orchestrator evidence-scout completed task_id=%s evidence=%s elapsed_ms=%.2f",
            task.task_id,
            len(evidence_result.get("evidence", [])),
            (perf_counter() - evidence_started_at) * 1000,
        )
        logger.info("[research-runtime] mock orchestrator critic start task_id=%s", task.task_id)
        critic_started_at = perf_counter()
        critic_result = self.registry.get("critic").run(task, ledger, trend_result, evidence_result)
        logger.info(
            "[research-runtime] mock orchestrator critic completed task_id=%s findings=%s elapsed_ms=%.2f",
            task.task_id,
            len(critic_result.get("findings", [])),
            (perf_counter() - critic_started_at) * 1000,
        )
        logger.info(
            "[research-runtime] mock orchestrator completed task_id=%s elapsed_ms=%.2f",
            task.task_id,
            (perf_counter() - started_at) * 1000,
        )
        return {
            "trend": trend_result,
            "evidence": evidence_result,
            "critic": critic_result,
        }
