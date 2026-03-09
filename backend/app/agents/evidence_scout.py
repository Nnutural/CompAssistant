from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.runtime_tools import build_evidence_tools, build_source_and_evidence_records
from app.schemas.research_runtime import AgentTaskEnvelope, EvidenceRecord, ResearchLedger, SourceRecord

try:
    from agents import Agent
except ImportError:
    Agent = None


class EvidenceScoutOutput(BaseModel):
    agent: str = 'evidence-scout'
    sources: list[SourceRecord]
    evidence: list[EvidenceRecord]
    notes: list[str] = Field(default_factory=list)


class EvidenceScoutAgent:
    name = 'evidence-scout'

    # Phase 3 fallback path. This stays offline and deterministic for local testing.
    def run(self, task: AgentTaskEnvelope, ledger: ResearchLedger, trend_result: dict) -> dict:
        directions = list(trend_result.get('directions', []))
        sources, evidence_items = build_source_and_evidence_records(task, directions, self.name)
        return {
            'agent': self.name,
            'sources': sources,
            'evidence': evidence_items,
            'notes': [f'Generated {len(evidence_items)} offline evidence records from {len(directions)} directions.'],
        }


def build_evidence_scout_agent(model: str):
    if Agent is None:
        raise RuntimeError('openai-agents is not installed')

    return build_evidence_scout_agent_with_mode(model=model, structured=True)


def build_evidence_scout_agent_with_mode(model: str, *, structured: bool):
    if Agent is None:
        raise RuntimeError('openai-agents is not installed')

    instructions = (
        'You are EvidenceScout, a specialist that turns provided directions into structured local source and evidence records. '
        'You must call the build_evidence_seed tool exactly once and keep the final answer grounded in that tool output. '
        'Do not claim network access or external retrieval. '
        'Phase 4 extension point: replace the local evidence seed tool with real retrieval and extraction tools.'
    )
    if structured:
        instructions += ' Return only structured output that matches EvidenceScoutOutput.'
    else:
        instructions += (
            ' Return only a JSON object with keys: agent, sources, evidence, notes. '
            'Do not wrap the JSON in markdown fences.'
        )

    return Agent(
        name='evidence-scout',
        model=model,
        tools=build_evidence_tools(),
        output_type=EvidenceScoutOutput if structured else None,
        instructions=instructions,
    )
