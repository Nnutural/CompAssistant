import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.output_repair import repair_output_to_model  # noqa: E402
from app.agents.output_validation import validate_output_against_model  # noqa: E402
from app.schemas.research_runtime import CompetitionRecommendationArtifact  # noqa: E402


class OutputRepairTests(unittest.TestCase):
    def test_repair_extracts_markdown_json_and_normalizes_nested_lists(self) -> None:
        raw_output = """```json
{
  "result": {
    "task_type": "competition_recommendation",
    "profile_summary": "方向=算法/编程; 年级=freshman; 能力标签=3 个",
    "recommendations": [
      {
        "competition_id": 14,
        "competition_name": "蓝桥杯全国软件和信息技术专业人才大赛",
        "match_score": "88.5",
        "reasons": "方向匹配, 入门友好",
        "risk_notes": "需要持续训练, 需要模板整理",
        "focus_tags": "algorithms, coding"
      }
    ],
    "risk_overview": "需要持续训练, 需要模板整理"
  }
}
```"""

        repaired = repair_output_to_model(raw_output, CompetitionRecommendationArtifact)
        validation = validate_output_against_model(repaired.repaired_output, CompetitionRecommendationArtifact)

        self.assertEqual(repaired.parse_errors, [])
        self.assertTrue(any("Unwrapped payload" in warning for warning in repaired.warnings))
        self.assertIsNotNone(validation.validated_output)
        self.assertEqual(validation.validated_output.recommendations[0].focus_tags, ["algorithms", "coding"])
        self.assertEqual(
            validation.validated_output.recommendations[0].risk_notes,
            ["需要持续训练", "需要模板整理"],
        )

    def test_validation_marks_empty_recommendations_for_review(self) -> None:
        validation = validate_output_against_model(
            {
                "task_type": "competition_recommendation",
                "profile_summary": "方向=综合/科技",
                "recommendations": [],
                "risk_overview": [],
            },
            CompetitionRecommendationArtifact,
        )

        self.assertTrue(validation.review_required)
        self.assertIn("recommendations", validation.review_message)


if __name__ == "__main__":
    unittest.main()
