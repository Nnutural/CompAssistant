from __future__ import annotations

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

        recommendations: list[dict] = []
        aggregated_risks: list[str] = []
        for item in filtered.get("matches", [])[:3]:
            competition = item["competition"]
            scoring = item["score_breakdown"]
            rationale = unwrap_tool_result(
                compose_recommendation_rationale(competition, scoring),
                "compose_recommendation_rationale",
            )
            recommendations.append(
                {
                    "competition_id": competition["id"],
                    "competition_name": competition["name"],
                    "match_score": scoring["total_score"],
                    "reasons": rationale["reasons"],
                    "risk_notes": rationale["risk_notes"],
                    "focus_tags": competition.get("enriched", {}).get("focus_tags", [])[:4],
                }
            )
            aggregated_risks.extend(rationale["risk_notes"])

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
        "Use the local competition filtering and rationale tools as grounding. "
        "Keep the output short, practical, and product-oriented. "
        "Do not invent competitions or external data."
    )
    if structured:
        instructions += " Return only structured output that matches CompetitionRecommendationArtifact."
    else:
        instructions += (
            " Return only a JSON object with keys: task_type, profile_summary, recommendations, risk_overview. "
            "Do not wrap the JSON in markdown fences."
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
    return f"方向={direction}; 年级={grade}; 能力标签={len(profile.get('ability_tags', []))} 个"
