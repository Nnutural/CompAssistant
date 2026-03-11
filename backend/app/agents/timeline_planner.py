from __future__ import annotations

from app.agents.schema_adapter import build_provider_output_schema
from app.schemas.research_runtime import AgentTaskEnvelope, CompetitionTimelineArtifact, ResearchLedger
from app.tools import build_timeline_template, unwrap_tool_result

try:
    from agents import Agent
except ImportError:
    Agent = None


class TimelinePlannerAgent:
    name = "timeline-planner"

    def run(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> dict:
        competition_id = int(task.payload["competition_id"])
        deadline = task.payload.get("deadline")
        constraints = task.payload.get("constraints") or {}
        result = unwrap_tool_result(
            build_timeline_template(competition_id, deadline, constraints),
            "build_timeline_template",
        )
        competition = result["competition"]
        return CompetitionTimelineArtifact(
            task_type="competition_timeline_plan",
            competition_id=competition["id"],
            competition_name=competition["name"],
            deadline=result["deadline"],
            preparation_checklist=result["preparation_checklist"],
            milestones=result["milestones"],
            stage_plan=result["stage_plan"],
            reverse_schedule=result["reverse_schedule"],
        ).model_dump(mode="json")


def build_timeline_planner_agent_with_mode(model: str, *, structured: bool, tools: list | None = None):
    if Agent is None:
        raise RuntimeError("openai-agents is not installed")

    instructions = (
        "You are TimelinePlanner, a specialist for turning a competition deadline into a short reverse schedule. "
        "Use local timeline templates and constraints only. "
        "Do not invent external calendar events."
    )
    if structured:
        instructions += (
            " Return raw JSON only, with no prose, no markdown fences, and no wrapper text. "
            "The top-level object must match CompetitionTimelineArtifact exactly. "
            "Do not add extra commentary fields."
        )
    else:
        instructions += (
            " Return only a JSON object with keys: task_type, competition_id, competition_name, deadline, "
            "preparation_checklist, milestones, stage_plan, reverse_schedule. "
            "Do not wrap the JSON in markdown fences, and do not add prose before or after the JSON."
        )

    return Agent(
        name="timeline-planner",
        model=model,
        tools=tools or [],
        output_type=build_provider_output_schema(CompetitionTimelineArtifact) if structured else None,
        instructions=instructions,
    )
