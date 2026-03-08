from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.runtime_tools import build_critic_assessment, build_critic_findings, build_critic_tools, resolve_topic
from app.schemas.research_runtime import AgentTaskEnvelope, FindingItem, ResearchLedger

try:
    from agents import Agent
except ImportError:
    Agent = None


class CriticOutput(BaseModel):
    agent: str = 'critic'
    assessment: dict[str, str]
    findings: list[FindingItem]
    notes: list[str] = Field(default_factory=list)


class CriticAgent:
    name = 'critic'

    # Phase 3 fallback path. This stays deterministic for local testing without the SDK.
    def run(self, task: AgentTaskEnvelope, ledger: ResearchLedger, trend_result: dict, evidence_result: dict) -> dict:
        evidence_ids = [item.evidence_id for item in evidence_result.get('evidence', [])]
        assessment = build_critic_assessment(resolve_topic(task, ledger), len(trend_result.get('directions', [])), len(evidence_ids))
        findings = build_critic_findings(task.task_id, evidence_ids)
        return {
            'agent': self.name,
            'assessment': assessment,
            'findings': findings,
            'notes': list(assessment.values()),
        }


def build_critic_agent(model: str):
    if Agent is None:
        raise RuntimeError('openai-agents is not installed')

    return Agent(
        name='critic',
        model=model,
        tools=build_critic_tools(),
        output_type=CriticOutput,
        instructions=(
            'You are Critic, a specialist that evaluates novelty, feasibility, and risk for the current research runtime output. '
            'You must call the score_runtime_output tool exactly once and ground your final output in that tool result. '
            'Return only structured output that matches CriticOutput. '
            'Do not claim external validation. '
            'Phase 4 extension point: enrich this agent with stronger evidence review and provenance-aware critique.'
        ),
    )
