from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.runtime_tools import build_trend_tools, generate_candidate_directions, resolve_topic
from app.schemas.research_runtime import AgentTaskEnvelope, ResearchLedger

try:
    from agents import Agent
except ImportError:
    Agent = None


class TrendScoutOutput(BaseModel):
    agent: str = 'trend-scout'
    directions: list[str]
    notes: list[str] = Field(default_factory=list)


class TrendScoutAgent:
    name = 'trend-scout'

    # Phase 3 fallback path. This stays deterministic for local testing without an API key.
    def run(self, task: AgentTaskEnvelope, ledger: ResearchLedger) -> dict:
        topic = resolve_topic(task, ledger)
        directions = generate_candidate_directions(topic, task.objective)
        return {
            'agent': self.name,
            'directions': directions,
            'notes': [
                f"Generated {len(directions)} candidate directions for topic '{topic}'.",
                f'Objective context: {task.objective.strip()}',
            ],
        }


def build_trend_scout_agent(model: str):
    if Agent is None:
        raise RuntimeError('openai-agents is not installed')

    return Agent(
        name='trend-scout',
        model=model,
        tools=build_trend_tools(),
        output_type=TrendScoutOutput,
        instructions=(
            'You are TrendScout, a specialist that proposes 2 to 3 candidate research directions. '
            'You must call the generate_candidate_directions tool exactly once and ground your final output in that tool result. '
            'Return only structured output that matches TrendScoutOutput. '
            'Do not invent web search results or external citations. '
            'Phase 4 extension point: replace the local direction tool with network-backed discovery tools.'
        ),
    )
