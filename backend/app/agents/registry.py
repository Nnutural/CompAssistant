from app.agents.critic import CriticAgent
from app.agents.evidence_scout import EvidenceScoutAgent
from app.agents.trend_scout import TrendScoutAgent


class MockAgentRegistry:
    def __init__(self):
        self._agents = {
            "trend-scout": TrendScoutAgent(),
            "evidence-scout": EvidenceScoutAgent(),
            "critic": CriticAgent(),
        }

    def get(self, name: str):
        return self._agents[name]