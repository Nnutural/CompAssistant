import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.runtime_tools import _build_provider_recommendation_match  # noqa: E402


class RuntimeToolsTests(unittest.TestCase):
    def test_provider_recommendation_match_returns_canonical_recommendation_payload(self) -> None:
        item = {
            "competition": {
                "id": 13,
                "name": "全国大学生信息安全竞赛",
                "field": "网络安全",
                "difficulty": "中等",
                "level": "A",
                "deadline": "2026-06-05T18:00:00",
                "enriched": {"focus_tags": ["security", "ctf", "attack-defense", "analysis"]},
            },
            "score_breakdown": {
                "total_score": 93.43,
                "difficulty_gap": "aligned",
                "component_scores": {
                    "field_alignment": 35.0,
                    "grade_alignment": 20.0,
                    "ability_alignment": 21.43,
                    "preference_alignment": 7.0,
                    "difficulty_alignment": 10.0,
                    "level_bonus": 0.0,
                },
                "direction_score": None,
                "ability_score": None,
            },
        }

        serialized = _build_provider_recommendation_match(item)

        self.assertEqual(serialized["competition_id"], 13)
        self.assertEqual(serialized["competition_name"], item["competition"]["name"])
        self.assertEqual(serialized["match_score"], 93.43)
        self.assertTrue(serialized["reasons"])
        self.assertIn("risk_notes", serialized)
        self.assertEqual(serialized["match_context"]["difficulty_gap"], "aligned")
        self.assertIn("component_scores", serialized["match_context"])
        self.assertNotIn("direction_score", serialized["match_context"]["component_scores"])
        self.assertNotIn("ability_score", serialized["match_context"]["component_scores"])


if __name__ == "__main__":
    unittest.main()
