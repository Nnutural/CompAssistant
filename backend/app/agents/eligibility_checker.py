from __future__ import annotations

from app.agents.local_knowledge import find_local_knowledge_for_competition
from app.agents.schema_adapter import build_provider_output_schema
from app.schemas.research_runtime import AgentTaskEnvelope, CompetitionEligibilityArtifact, ResearchLedger
from app.tools import check_eligibility_rules, unwrap_tool_result

try:
    from agents import Agent
except ImportError:
    Agent = None


class EligibilityCheckerAgent:
    name = "eligibility-checker"

    def run(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> dict:
        competition_id = int(task.payload["competition_id"])
        profile = task.payload.get("profile") or task.payload.get("user_profile") or {}
        result = unwrap_tool_result(
            check_eligibility_rules(competition_id, profile),
            "check_eligibility_rules",
        )
        competition = result["competition"]
        local_knowledge = find_local_knowledge_for_competition(competition_id, profile)
        attention_points = list(result["attention_points"])
        rationale = list(result["rationale"])
        for item in local_knowledge:
            reference_note = f"Local knowledge reference: {item.title} ({item.source_name})"
            if reference_note not in attention_points:
                attention_points.append(reference_note)
            grounded_rationale = f"Grounded with local document '{item.title}': {item.summary or item.url}"
            if grounded_rationale not in rationale:
                rationale.append(grounded_rationale)
        return CompetitionEligibilityArtifact(
            task_type="competition_eligibility_check",
            competition_id=competition["id"],
            competition_name=competition["name"],
            eligibility_label=result["eligibility_label"],
            is_eligible=result["is_eligible"],
            missing_conditions=result["missing_conditions"],
            attention_points=attention_points,
            rationale=rationale,
        ).model_dump(mode="json")


def build_eligibility_checker_agent_with_mode(model: str, *, structured: bool, tools: list | None = None):
    if Agent is None:
        raise RuntimeError("openai-agents is not installed")

    instructions = (
        "You are EligibilityChecker, a specialist for deciding whether a student profile should join a competition. "
        "Use local eligibility rules and competition metadata only. "
        "If the input JSON contains local_knowledge records, use them as local retrieval grounding. "
        "Do not claim formal official eligibility; focus on product-level suitability and missing conditions."
    )
    if structured:
        instructions += (
            " Return raw JSON only, with no prose, no markdown fences, and no wrapper text. "
            "The top-level object must match CompetitionEligibilityArtifact exactly. "
            "Do not add any extra fields beyond task_type, competition_id, competition_name, eligibility_label, "
            "is_eligible, missing_conditions, attention_points, rationale."
        )
    else:
        instructions += (
            " Return only a JSON object with keys: task_type, competition_id, competition_name, eligibility_label, "
            "is_eligible, missing_conditions, attention_points, rationale. "
            "Do not wrap the JSON in markdown fences, and do not add prose before or after the JSON."
        )

    return Agent(
        name="eligibility-checker",
        model=model,
        tools=tools or [],
        output_type=build_provider_output_schema(CompetitionEligibilityArtifact) if structured else None,
        instructions=instructions,
    )
