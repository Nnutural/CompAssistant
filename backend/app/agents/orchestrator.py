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
        if task.task_type == "competition_recommendation":
            output = self.registry.get("competition-recommender").run(task, ledger)
            logger.info(
                "[research-runtime] mock orchestrator recommendation completed task_id=%s recommendations=%s elapsed_ms=%.2f",
                task.task_id,
                len(output.get("recommendations", [])),
                (perf_counter() - started_at) * 1000,
            )
            return {
                "flow": task.task_type,
                "specialist_name": "competition-recommender",
                "specialist_output": output,
            }

        if task.task_type == "competition_eligibility_check":
            output = self.registry.get("eligibility-checker").run(task, ledger)
            logger.info(
                "[research-runtime] mock orchestrator eligibility completed task_id=%s missing_conditions=%s elapsed_ms=%.2f",
                task.task_id,
                len(output.get("missing_conditions", [])),
                (perf_counter() - started_at) * 1000,
            )
            return {
                "flow": task.task_type,
                "specialist_name": "eligibility-checker",
                "specialist_output": output,
            }

        if task.task_type == "competition_timeline_plan":
            output = self.registry.get("timeline-planner").run(task, ledger)
            logger.info(
                "[research-runtime] mock orchestrator timeline completed task_id=%s milestones=%s elapsed_ms=%.2f",
                task.task_id,
                len(output.get("milestones", [])),
                (perf_counter() - started_at) * 1000,
            )
            return {
                "flow": task.task_type,
                "specialist_name": "timeline-planner",
                "specialist_output": output,
            }

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
            "flow": task.task_type,
            "trend": trend_result,
            "evidence": evidence_result,
            "critic": critic_result,
        }
