from app.agents.competition_recommender import CompetitionRecommenderAgent
from app.agents.critic import CriticAgent
from app.agents.evidence_scout import EvidenceScoutAgent
from app.agents.eligibility_checker import EligibilityCheckerAgent
from app.agents.timeline_planner import TimelinePlannerAgent
from app.agents.trend_scout import TrendScoutAgent


class MockAgentRegistry:
    def __init__(self):
        self._agents = {
            "competition-recommender": CompetitionRecommenderAgent(),
            "eligibility-checker": EligibilityCheckerAgent(),
            "timeline-planner": TimelinePlannerAgent(),
            "trend-scout": TrendScoutAgent(),
            "evidence-scout": EvidenceScoutAgent(),
            "critic": CriticAgent(),
        }

    def get(self, name: str):
        return self._agents[name]
