from __future__ import annotations

from app.agents.local_knowledge import find_local_knowledge_for_recommendation
from app.agents.schema_adapter import build_provider_output_schema
from app.schemas.research_runtime import AgentTaskEnvelope, CompetitionRecommendationArtifact, ResearchLedger
from app.tools import (
    compose_recommendation_rationale,
    filter_competitions_by_profile,
    unwrap_tool_result,
)

try:
    from agents import Agent
except ImportError:
    Agent = None


class CompetitionRecommenderAgent:
    name = "competition-recommender"

    def run(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> dict:
        profile = _resolve_profile(task.payload)
        filtered = unwrap_tool_result(filter_competitions_by_profile(profile), "filter_competitions_by_profile")
        local_knowledge = find_local_knowledge_for_recommendation(profile)

        recommendations: list[dict] = []
        aggregated_risks: list[str] = []
        for item in filtered.get("matches", [])[:3]:
            competition = item["competition"]
            scoring = item["score_breakdown"]
            rationale = unwrap_tool_result(
                compose_recommendation_rationale(competition, scoring),
                "compose_recommendation_rationale",
            )
            reasons = list(rationale["reasons"])
            for hit in local_knowledge[:2]:
                reference_note = f"Local knowledge: {hit.title} [{hit.source_type}]"
                if reference_note not in reasons:
                    reasons.append(reference_note)
            recommendations.append(
                {
                    "competition_id": competition["id"],
                    "competition_name": competition["name"],
                    "match_score": scoring["total_score"],
                    "reasons": reasons,
                    "risk_notes": rationale["risk_notes"],
                    "focus_tags": competition.get("enriched", {}).get("focus_tags", [])[:4],
                }
            )
            aggregated_risks.extend(rationale["risk_notes"])
        for hit in local_knowledge[:3]:
            local_note = f"Local grounding used: {hit.title} ({hit.source_type})"
            if local_note not in aggregated_risks:
                aggregated_risks.append(local_note)

        return CompetitionRecommendationArtifact(
            task_type="competition_recommendation",
            profile_summary=_profile_summary(profile, ledger.topic),
            recommendations=recommendations,
            risk_overview=list(dict.fromkeys(aggregated_risks))[:5],
        ).model_dump(mode="json")


def build_competition_recommender_agent_with_mode(model: str, *, structured: bool, tools: list | None = None):
    if Agent is None:
        raise RuntimeError("openai-agents is not installed")

    instructions = (
        "You are CompetitionRecommender, a specialist for university competition recommendation. "
        "Use the local competition filtering tool as grounding. "
        "If the input JSON includes local_knowledge records, use them as local retrieval grounding. "
        "Keep the output short, practical, and product-oriented. "
        "Do not invent competitions or external data."
    )
    if structured:
        instructions += (
            " Return raw JSON only, with no prose, no markdown fences, and no wrapper text. "
            "Call filter_competitions_by_profile exactly once, select at most the top 3 matches, and stop. "
            "The tool already returns canonical recommendation fields plus reasons and risk notes. "
            "Copy those fields directly instead of renaming, nesting, or expanding them. "
            "The top-level object must match CompetitionRecommendationArtifact exactly. "
            "The top-level task_type must be exactly competition_recommendation. "
            "The top-level profile_summary is required and must be a short one-line summary of direction, grade, and ability profile. "
            "The top-level risk_overview must be an array of strings, never an object. "
            "Do not echo task_id, session_id, ledger_id, objective, profile, or any other input wrapper fields. "
            "Each recommendation item must contain only competition_id, competition_name, match_score, reasons, risk_notes, focus_tags. "
            "Build risk_overview by deduplicating the selected recommendation risk_notes. "
            "Do not nest a competition object and do not add extra fields such as score, difficulty, deadline, match_summary, recommendation_level, achievable_ideas, preparation_plan, or timeline_advice."
        )
    else:
        instructions += (
            " Return only a JSON object with keys: task_type, profile_summary, recommendations, risk_overview. "
            "Call filter_competitions_by_profile exactly once, select at most the top 3 matches, and stop. "
            "The tool already returns canonical recommendation fields plus reasons and risk notes. "
            "Do not wrap the JSON in markdown fences, and do not add prose before or after the JSON. "
            "The task_type must be exactly competition_recommendation, profile_summary is required, and risk_overview must be a JSON array of strings. "
            "Do not echo task_id, session_id, ledger_id, objective, or profile at the top level. "
            "Each recommendation item must contain only competition_id, competition_name, match_score, reasons, risk_notes, focus_tags."
        )

    return Agent(
        name="competition-recommender",
        model=model,
        tools=tools or [],
        output_type=build_provider_output_schema(CompetitionRecommendationArtifact) if structured else None,
        instructions=instructions,
    )


def _resolve_profile(payload: dict) -> dict:
    return payload.get("profile") or payload.get("user_profile") or {}


def _profile_summary(profile: dict, topic: str) -> str:
    direction = profile.get("direction") or profile.get("field") or topic
    grade = profile.get("grade") or "freshman"
    return f"direction={direction}; grade={grade}; ability_tags={len(profile.get('ability_tags', []))}"
